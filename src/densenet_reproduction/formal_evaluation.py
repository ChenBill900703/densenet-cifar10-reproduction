"""Later Phase 6 final-only evaluation adapter, unexecuted in Phase 5."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

import torch
from torch.utils.data import DataLoader, SequentialSampler

from .data import Cifar10BinaryDataset, verify_prepared_cifar10_split
from .formal_checkpoint import (
    FormalCheckpointProvenance,
    load_formal_checkpoint,
    read_formal_checkpoint_manifest,
)
from .mechanics import build_phase3_optimizer, build_project_seeded_model
from .phase5 import (
    LaunchIdentity,
    PHASE5_PROJECT_SEEDS,
    Phase6Authorization,
    canonical_json_bytes,
    expected_aggregate_fields,
    require_phase6_authorization,
    validate_aggregate_result,
    validate_launch_identity,
    validate_seed_result,
)


@dataclass(frozen=True, slots=True)
class FormalEvaluationRequest:
    prepared_directory: Path
    formal_root: Path
    master_seed: int
    device_index: int
    authorization: Phase6Authorization
    expected_launch: LaunchIdentity
    observed_launch: LaunchIdentity


def _write_new_fsynced(path: Path, document: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Immutable result target already exists: {path}")
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical_json_bytes(dict(document)))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        path.unlink(missing_ok=True)
        raise


def _append_test_progress(path: Path, document: Mapping[str, Any]) -> None:
    with path.open("ab", buffering=0) as stream:
        stream.write(canonical_json_bytes(dict(document)))
        os.fsync(stream.fileno())


def _seed_directory(root: Path, freeze_hash: str, seed: int) -> Path:
    path = root / freeze_hash / f"seed-{seed}"
    resolved = path.resolve(strict=True)
    if not resolved.is_dir() or path.is_symlink():
        raise ValueError("Formal seed directory is missing or unsafe.")
    return resolved


def _verify_all_training_complete(
    root: Path, freeze_hash: str
) -> dict[int, tuple[Path, dict[str, Any]]]:
    from .formal_runtime import _require_completed_formal_seed

    checkpoints: dict[int, tuple[Path, dict[str, Any]]] = {}
    for seed in PHASE5_PROJECT_SEEDS:
        seed_root = _seed_directory(root, freeze_hash, seed)
        _require_completed_formal_seed(
            seed_root, freeze_hash, seed, allow_final_test_evidence=True
        )
        checkpoint = seed_root / "epoch-300.pt"
        manifest = read_formal_checkpoint_manifest(checkpoint)
        if (
            manifest["completed_epoch"] != 300
            or manifest["master_seed"] != seed
            or manifest["accepted_trajectory_steps"] != 234_600
            or manifest["provenance"]["freeze_manifest_sha256"] != freeze_hash
        ):
            raise ValueError("Epoch-300 training artifact is incomplete or mismatched.")
        checkpoints[seed] = (checkpoint, manifest)
    return checkpoints


def run_formal_final_evaluation(request: FormalEvaluationRequest) -> Path:
    """Test one seed exactly once, only after all training artifacts verify."""

    validate_launch_identity(request.expected_launch, request.observed_launch)
    require_phase6_authorization(
        request.authorization,
        expected_freeze_manifest_sha256=request.expected_launch.freeze_manifest_sha256,
    )
    if request.master_seed not in PHASE5_PROJECT_SEEDS:
        raise ValueError("Evaluation seed is not approved.")
    root = request.formal_root.resolve(strict=True)
    checkpoints = _verify_all_training_complete(
        root, request.expected_launch.freeze_manifest_sha256
    )
    seed_index = PHASE5_PROJECT_SEEDS.index(request.master_seed)
    for earlier_seed in PHASE5_PROJECT_SEEDS[:seed_index]:
        earlier_root = _seed_directory(
            root, request.expected_launch.freeze_manifest_sha256, earlier_seed
        )
        if not (earlier_root / "final-test-result.json").is_file():
            raise RuntimeError("Final evaluation seed order would be violated.")
    for later_seed in PHASE5_PROJECT_SEEDS[seed_index + 1 :]:
        later_root = _seed_directory(
            root, request.expected_launch.freeze_manifest_sha256, later_seed
        )
        if (later_root / "final-test-attempt.json").exists():
            raise RuntimeError("A later seed already has a final-test attempt.")
    prepared_verification = verify_prepared_cifar10_split(
        request.prepared_directory,
        split="test",
        expected_archive_sha256=request.expected_launch.dataset_sha256,
    )
    seed_root = _seed_directory(
        root, request.expected_launch.freeze_manifest_sha256, request.master_seed
    )
    attempt_path = seed_root / "final-test-attempt.json"
    progress_path = seed_root / "final-test-progress.jsonl"
    result_path = seed_root / "final-test-result.json"
    if attempt_path.exists() or progress_path.exists() or result_path.exists():
        raise RuntimeError(
            "Final-test attempt already exists; interruption/retry requires a new human decision."
        )
    _write_new_fsynced(
        attempt_path,
        {
            "classification": "FORMAL-FINAL-TEST-ATTEMPT-V1",
            "freeze_manifest_sha256": request.expected_launch.freeze_manifest_sha256,
            "master_seed": request.master_seed,
            "test_records_completed": 0,
        },
    )
    descriptor = os.open(
        progress_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
    )
    os.close(descriptor)
    # No test dataset is constructed before every checkpoint and attempt/order
    # gate above has passed.
    device = torch.device(f"cuda:{request.device_index}")
    model = build_project_seeded_model(request.master_seed).to(device)
    optimizer = build_phase3_optimizer(model, epoch=300)
    checkpoint, manifest = checkpoints[request.master_seed]
    provenance = FormalCheckpointProvenance(**manifest["provenance"])
    load_formal_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=seed_root,
        model=model,
        optimizer=optimizer,
        expected_master_seed=request.master_seed,
        expected_provenance=provenance,
        expected_cuda_device_indices=(request.device_index,),
    )
    dataset = Cifar10BinaryDataset(prepared_verification.directory, split="test")
    incorrect = 0
    total = 0
    model.eval()
    try:
        loader = DataLoader(
            dataset,
            batch_size=64,
            sampler=SequentialSampler(dataset),
            num_workers=0,
            drop_last=False,
            pin_memory=False,
        )
        with torch.inference_mode():
            for batch_index, (cpu_inputs, cpu_targets) in enumerate(loader):
                inputs = cpu_inputs.to(device, dtype=torch.float32, non_blocking=False)
                targets = cpu_targets.to(device, dtype=torch.long, non_blocking=False)
                logits = model(inputs)
                if tuple(logits.shape) != (targets.shape[0], 10) or not bool(
                    torch.isfinite(logits).all()
                ):
                    raise RuntimeError("Final-test raw-logit contract failed.")
                incorrect += int((torch.argmax(logits, dim=1) != targets).sum().item())
                total += int(targets.shape[0])
                _append_test_progress(
                    progress_path,
                    {
                        "batch_index": batch_index,
                        "classification": "FORMAL-FINAL-TEST-PROGRESS-V1",
                        "incorrect_count_so_far": incorrect,
                        "master_seed": request.master_seed,
                        "test_records_completed": total,
                    },
                )
    finally:
        dataset.close()
    if total != 10_000:
        raise RuntimeError("Final-test attempt did not complete exactly 10,000 records.")
    result = {
        "checkpoint_epoch": 300,
        "classification": "FORMAL-FINAL-TEST-RESULT-V1",
        "freeze_manifest_sha256": request.expected_launch.freeze_manifest_sha256,
        "incorrect_count": incorrect,
        "master_seed": request.master_seed,
        "test_attempts": 1,
        "test_records": total,
    }
    validate_seed_result(result)
    _write_new_fsynced(result_path, result)
    return result_path


def write_formal_aggregate(
    formal_root: Path,
    freeze_hash: str,
    *,
    authorization: Phase6Authorization,
    expected_launch: LaunchIdentity,
    observed_launch: LaunchIdentity,
) -> Path:
    """Aggregate exactly the three immutable integer results, once."""

    validate_launch_identity(expected_launch, observed_launch)
    require_phase6_authorization(
        authorization, expected_freeze_manifest_sha256=freeze_hash
    )
    root = formal_root.resolve(strict=True)
    counts: list[int] = []
    for seed in PHASE5_PROJECT_SEEDS:
        path = _seed_directory(root, freeze_hash, seed) / "final-test-result.json"
        if path.is_symlink() or not path.is_file():
            raise ValueError("All three final-test results must exist before aggregation.")
        document = json.loads(path.read_text(encoding="ascii"))
        validate_seed_result(document)
        if document["master_seed"] != seed or document["freeze_manifest_sha256"] != freeze_hash:
            raise ValueError("Final-test result identity mismatch.")
        counts.append(document["incorrect_count"])
    aggregate = {
        "classification": "FORMAL-AGGREGATE-RESULT-V1",
        "freeze_manifest_sha256": freeze_hash,
        "seeds": list(PHASE5_PROJECT_SEEDS),
        "selection": "none",
        **expected_aggregate_fields(counts),
    }
    validate_aggregate_result(aggregate)
    target = root / freeze_hash / "aggregate-result.json"
    _write_new_fsynced(target, aggregate)
    return target
