"""Deterministic GPU replay for authorized Phase 3 synthetic mechanics.

The worker performs optimizer steps only on tensors made by the generated-data
factory.  It never opens CIFAR, produces predictions/accuracy, downloads
weights, or performs a formal optimizer step.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import torch

from densenet_reproduction import (
    CheckpointProvenance,
    PROJECT_REPRODUCTION_SEEDS,
    SyntheticStepLedger,
    build_phase3_optimizer,
    build_project_seeded_model,
    initialize_runtime_rngs,
    load_phase3_checkpoint,
    make_synthetic_mechanics_batch,
    runtime_seed_bundle,
    save_phase3_checkpoint,
    state_dict_sha256,
    synthetic_mechanics_step,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_SHA256 = "C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _source_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    return completed.stdout.decode("ascii").strip()


def _optimizer_states_equal(
    first: torch.optim.Optimizer, second: torch.optim.Optimizer
) -> bool:
    first_state = first.state_dict()
    second_state = second.state_dict()
    if first_state["param_groups"] != second_state["param_groups"]:
        return False
    if set(first_state["state"]) != set(second_state["state"]):
        return False
    for parameter_id, values in first_state["state"].items():
        other_values = second_state["state"][parameter_id]
        if set(values) != set(other_values):
            return False
        for name, value in values.items():
            other = other_values[name]
            if isinstance(value, torch.Tensor):
                if not torch.equal(value.detach().cpu(), other.detach().cpu()):
                    return False
            elif value != other:
                return False
    return True


def _worker() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; Phase 3 GPU diagnostic did not run.")
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        raise RuntimeError("CUBLAS_WORKSPACE_CONFIG must be set before Python starts.")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.conv.fp32_precision = "ieee"
    torch.backends.cuda.matmul.fp32_precision = "ieee"

    device = torch.device("cuda:0")
    master_seed = PROJECT_REPRODUCTION_SEEDS[0]
    seed_bundle = runtime_seed_bundle(master_seed, cuda_device_indices=(0,))
    provenance = CheckpointProvenance(
        source_commit=_source_commit(),
        environment_lock_sha256=_sha256_file(
            PROJECT_ROOT / "requirements" / "environment-lock.txt"
        ),
        dataset_sha256=DATASET_SHA256,
        config_sha256=_sha256_file(
            PROJECT_ROOT / "docs" / "phase3_entry_decision_proposal.md"
        ),
    )
    batches = [
        make_synthetic_mechanics_batch(
            batch_size=2, generation_seed=53_000 + index, device=device
        )
        for index in range(1, 4)
    ]

    continuous_model = build_project_seeded_model(master_seed)
    initialize_runtime_rngs(seed_bundle)
    continuous_model.to(device)
    continuous_optimizer = build_phase3_optimizer(continuous_model)
    continuous_ledger = SyntheticStepLedger()
    first_loss = synthetic_mechanics_step(
        model=continuous_model,
        optimizer=continuous_optimizer,
        batch=batches[0],
        epoch=1,
        ledger=continuous_ledger,
    )
    with tempfile.TemporaryDirectory(prefix="densenet-phase3-") as temporary:
        checkpoint = Path(temporary) / "epoch_001.pt"
        manifest = save_phase3_checkpoint(
            checkpoint_path=checkpoint,
            allowed_root=Path(temporary),
            model=continuous_model,
            optimizer=continuous_optimizer,
            ledger=continuous_ledger,
            completed_epoch=1,
            master_seed=master_seed,
            provenance=provenance,
            cuda_device_indices=(0,),
        )
        continuous_losses = [first_loss]
        for epoch, batch in zip((2, 3), batches[1:], strict=True):
            continuous_losses.append(
                synthetic_mechanics_step(
                    model=continuous_model,
                    optimizer=continuous_optimizer,
                    batch=batch,
                    epoch=epoch,
                    ledger=continuous_ledger,
                )
            )

        resumed_model = build_project_seeded_model(master_seed).to(device)
        resumed_optimizer = build_phase3_optimizer(resumed_model)
        load_result = load_phase3_checkpoint(
            checkpoint_path=checkpoint,
            allowed_root=Path(temporary),
            model=resumed_model,
            optimizer=resumed_optimizer,
            expected_master_seed=master_seed,
            expected_provenance=provenance,
            expected_cuda_device_indices=(0,),
        )
        resumed_ledger = SyntheticStepLedger(load_result.synthetic_optimizer_steps)
        resumed_losses: list[torch.Tensor] = []
        for epoch, batch in zip((2, 3), batches[1:], strict=True):
            resumed_losses.append(
                synthetic_mechanics_step(
                    model=resumed_model,
                    optimizer=resumed_optimizer,
                    batch=batch,
                    epoch=epoch,
                    ledger=resumed_ledger,
                )
            )
        torch.cuda.synchronize(device)

        loss_replay_exact = all(
            torch.equal(left, right)
            for left, right in zip(continuous_losses[1:], resumed_losses, strict=True)
        )
        model_replay_exact = state_dict_sha256(continuous_model) == state_dict_sha256(
            resumed_model
        )
        optimizer_replay_exact = _optimizer_states_equal(
            continuous_optimizer, resumed_optimizer
        )
        if not (loss_replay_exact and model_replay_exact and optimizer_replay_exact):
            raise RuntimeError("Deterministic checkpoint replay was not bit exact.")

        print(
            json.dumps(
                {
                    "classification": "NON-FORMAL-SYNTHETIC-OPTIMIZER-MECHANICS",
                    "evidence_class": "DERIVED",
                    "scope": {
                        "cifar_samples_read": 0,
                        "predictions_computed": 0,
                        "accuracy_computations": 0,
                        "pretrained_downloads": 0,
                        "formal_optimizer_steps": 0,
                        "synthetic_optimizer_calls_executed": 5,
                        "synthetic_steps_per_compared_trajectory": 3,
                    },
                    "replay": {
                        "checkpoint_completed_epoch": load_result.completed_epoch,
                        "checkpoint_next_epoch": load_result.next_epoch,
                        "checkpoint_sha256": manifest["sha256"],
                        "losses_bit_exact": loss_replay_exact,
                        "model_state_bit_exact": model_replay_exact,
                        "optimizer_state_bit_exact": optimizer_replay_exact,
                        "final_model_state_sha256": state_dict_sha256(continuous_model),
                    },
                    "provenance": {
                        "source_commit": provenance.source_commit,
                        "environment_lock_sha256": provenance.environment_lock_sha256,
                        "dataset_sha256_recorded_only_not_read": provenance.dataset_sha256,
                        "candidate_config_sha256": provenance.config_sha256,
                    },
                    "rng": {
                        "policy": "sha256-domain-separated-runtime-v1",
                        "master_seed": master_seed,
                        "model_init_seed": seed_bundle.model_init,
                        "python_runtime_seed": seed_bundle.python_runtime,
                        "torch_cpu_runtime_seed": seed_bundle.torch_cpu_runtime,
                        "torch_cuda_runtime_seed": seed_bundle.torch_cuda_runtime[0][1],
                    },
                    "runtime": {
                        "torch": torch.__version__,
                        "cuda": torch.version.cuda,
                        "cudnn": torch.backends.cudnn.version(),
                        "device": torch.cuda.get_device_name(device),
                        "compute_capability": list(torch.cuda.get_device_capability(device)),
                        "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
                        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                        "cudnn_benchmark": torch.backends.cudnn.benchmark,
                        "cudnn_deterministic": torch.backends.cudnn.deterministic,
                        "cudnn_convolution_fp32_precision": torch.backends.cudnn.conv.fp32_precision,
                        "matmul_fp32_precision": torch.backends.cuda.matmul.fp32_precision,
                        "amp_used": False,
                        "compile_used": False,
                        "recomputation_used": False,
                        "runtime_rngs_initialized_from_approved_bundle": True,
                    },
                },
                sort_keys=True,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    if arguments.worker:
        _worker()
        return
    environment = os.environ.copy()
    environment["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    environment["PYTHONHASHSEED"] = "0"
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--worker"],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    report: dict[str, Any] = json.loads(completed.stdout.decode("utf-8"))
    report["record_date"] = date.today().isoformat()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
