"""Fail-closed CLI for the frozen formal training/evaluation adapters.

During Phase 5 only ``describe`` may be run. The other commands require later
canonical Phase 5-completion and Phase 6-entry decision artifacts and the exact
frozen launch environment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from densenet_reproduction.data import verify_prepared_cifar10_split
from densenet_reproduction.formal_checkpoint import FormalCheckpointProvenance
from densenet_reproduction.formal_evaluation import (
    FormalEvaluationRequest,
    run_formal_final_evaluation,
    write_formal_aggregate,
)
from densenet_reproduction.formal_runtime import (
    require_create_new_formal_run_root,
    require_formal_seed_training_order,
)
from densenet_reproduction.formal_training import (
    FormalTrainingRequest,
    enforce_formal_runtime_policy,
    run_formal_training_seed,
)
from densenet_reproduction.phase5 import (
    PHASE5_ACCEPTED_STEPS_PER_SEED,
    PHASE5_PROJECT_SEEDS,
    Phase6Authorization,
    read_canonical_json,
    validate_formal_config,
    verify_phase6_decision_artifacts,
)
from densenet_reproduction.phase5_launch import (
    expected_launch_identity,
    observe_and_validate_launch,
)


def _authorization(path: Path) -> Phase6Authorization:
    document = read_canonical_json(path)
    if not isinstance(document, dict) or set(document) != {
        "freeze_manifest_sha256",
        "phase5_completion_decision_sha256",
        "phase6_entry_decision_sha256",
    }:
        raise ValueError("Unexpected Phase 6 authorization schema.")
    return Phase6Authorization(**document)


def _required_path(arguments: argparse.Namespace, name: str) -> Path:
    value = getattr(arguments, name)
    if value is None:
        raise ValueError(f"--{name.replace('_', '-')} is required for this command.")
    return value


def _preflight(arguments: argparse.Namespace):
    authorization = _authorization(_required_path(arguments, "authorization"))
    enforce_formal_runtime_policy(arguments.device_index)
    manifest, observed = observe_and_validate_launch(
        freeze_manifest_path=_required_path(arguments, "freeze_manifest"),
        config_path=arguments.config,
        dataset_archive_path=_required_path(arguments, "dataset_archive"),
        project_wheel_path=_required_path(arguments, "project_wheel"),
        python_runtime_archive_path=_required_path(arguments, "python_runtime_archive"),
        python_runtime_manifest_path=_required_path(arguments, "python_runtime_manifest"),
        installed_environment_manifest_path=_required_path(
            arguments, "installed_environment_manifest"
        ),
        device_index=arguments.device_index,
    )
    expected_hash = authorization.freeze_manifest_sha256
    if observed.freeze_manifest_sha256 != expected_hash:
        raise PermissionError("Authorization and observed freeze manifest differ.")
    verify_phase6_decision_artifacts(
        authorization,
        expected_freeze_manifest_sha256=observed.freeze_manifest_sha256,
        phase5_completion_decision_path=_required_path(
            arguments, "phase5_completion_decision"
        ),
        phase6_entry_decision_path=_required_path(arguments, "phase6_entry_decision"),
    )
    prepared_verification = None
    if arguments.command == "train":
        prepared_verification = verify_prepared_cifar10_split(
            _required_path(arguments, "prepared_directory"),
            split="train",
            expected_archive_sha256=observed.dataset_sha256,
        )
    formal_root = _required_path(arguments, "formal_root").resolve(strict=True)
    free_bytes = shutil.disk_usage(formal_root).free
    if free_bytes < manifest["storage"]["required_bytes"]:
        raise RuntimeError("Current free disk is below the frozen storage gate.")
    return authorization, manifest, observed, formal_root, prepared_verification


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("describe", "train", "evaluate", "aggregate"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--freeze-manifest", type=Path)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--phase5-completion-decision", type=Path)
    parser.add_argument("--phase6-entry-decision", type=Path)
    parser.add_argument("--dataset-archive", type=Path)
    parser.add_argument("--project-wheel", type=Path)
    parser.add_argument("--python-runtime-archive", type=Path)
    parser.add_argument("--python-runtime-manifest", type=Path)
    parser.add_argument("--installed-environment-manifest", type=Path)
    parser.add_argument("--prepared-directory", type=Path)
    parser.add_argument("--formal-root", type=Path)
    resume_group = parser.add_mutually_exclusive_group()
    resume_group.add_argument("--resume-checkpoint", type=Path)
    resume_group.add_argument("--resume-initial-boundary", action="store_true")
    parser.add_argument("--seed", type=int, choices=PHASE5_PROJECT_SEEDS)
    parser.add_argument("--device-index", type=int, default=0)
    arguments = parser.parse_args()
    config = validate_formal_config(arguments.config)
    if arguments.command == "describe":
        print(
            json.dumps(
                {
                    "accepted_steps_per_seed": PHASE5_ACCEPTED_STEPS_PER_SEED,
                    "classification": "PHASE5-STATIC-FORMAL-RUNNER-DESCRIPTION",
                    "formal_optimizer_steps": 0,
                    "model_or_dataset_constructed": False,
                    "seeds": list(PHASE5_PROJECT_SEEDS),
                    "target_slug": config["target_slug"],
                },
                sort_keys=True,
            )
        )
        return 0
    authorization, manifest, observed, formal_root, prepared_verification = _preflight(
        arguments
    )
    expected = expected_launch_identity(manifest, observed.freeze_manifest_sha256)
    if arguments.command == "train":
        if arguments.seed is None:
            raise ValueError("--seed is required for training.")
        if prepared_verification is None:
            raise RuntimeError("Training prepared preflight was not completed.")
        prepared = prepared_verification.directory
        if arguments.resume_checkpoint is None and not arguments.resume_initial_boundary:
            run_directory = require_create_new_formal_run_root(
                formal_root, observed.freeze_manifest_sha256, arguments.seed
            )
        else:
            run_directory = require_formal_seed_training_order(
                formal_root,
                observed.freeze_manifest_sha256,
                arguments.seed,
                resuming=True,
            )
        provenance = FormalCheckpointProvenance(
            freeze_manifest_sha256=observed.freeze_manifest_sha256,
            source_commit=manifest["source"]["freeze_source_commit"],
            project_wheel_sha256=observed.project_wheel_sha256,
            environment_manifest_sha256=observed.environment_manifest_sha256,
            dataset_sha256=observed.dataset_sha256,
            config_sha256=observed.config_sha256,
            ledger_head_sha256="0" * 64,
        )
        checkpoints = run_formal_training_seed(
            FormalTrainingRequest(
                prepared_directory=prepared,
                run_directory=run_directory,
                master_seed=arguments.seed,
                device_index=arguments.device_index,
                authorization=authorization,
                expected_launch=expected,
                observed_launch=observed,
                base_provenance=provenance,
                resume_checkpoint=arguments.resume_checkpoint,
                resume_initial_boundary=arguments.resume_initial_boundary,
            )
        )
        print(json.dumps({"published_checkpoints": [str(path) for path in checkpoints]}))
        return 0
    if arguments.command == "evaluate":
        if arguments.seed is None:
            raise ValueError("--seed is required for evaluation.")
        result = run_formal_final_evaluation(
            FormalEvaluationRequest(
                prepared_directory=_required_path(arguments, "prepared_directory"),
                formal_root=formal_root,
                master_seed=arguments.seed,
                device_index=arguments.device_index,
                authorization=authorization,
                expected_launch=expected,
                observed_launch=observed,
            )
        )
        print(result)
        return 0
    result = write_formal_aggregate(
        formal_root,
        observed.freeze_manifest_sha256,
        authorization=authorization,
        expected_launch=expected,
        observed_launch=observed,
    )
    print(result)
    return 0


def main_entry() -> None:
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, TypeError, ValueError, PermissionError) as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main_entry()
