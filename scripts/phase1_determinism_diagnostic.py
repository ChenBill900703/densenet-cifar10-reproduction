"""Fresh-process CUDA gradient replay diagnostic for Phase 1.

All inputs are generated, no optimizer is constructed or stepped, and no formal
training run is performed. The explicit deterministic settings are diagnostic
candidates rather than an approved formal policy. The parent process launches
independent workers so replay claims do not depend on residual CUDA state in one
process.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import torch
from torch import nn

from densenet_reproduction import build_formal_model, state_dict_sha256


MODEL_TEST_SEED = 27_000
INPUT_TEST_SEED = 27_001
RUNS_PER_MODE = 3


def _update_tensor_hash(
    digest: Any, name: str, tensor: torch.Tensor
) -> None:
    contiguous = tensor.detach().cpu().contiguous()
    # Preserve the exact metadata framing used by the recovered independent
    # audit so its historical hashes remain directly comparable.
    digest.update(name.encode("utf-8"))
    digest.update(str(contiguous.dtype).encode("utf-8"))
    digest.update(str(tuple(contiguous.shape)).encode("utf-8"))
    raw = bytes(contiguous.reshape(-1).view(torch.uint8).tolist())
    digest.update(raw)


def _tensor_sha256(name: str, tensor: torch.Tensor) -> str:
    digest = hashlib.sha256()
    _update_tensor_hash(digest, name, tensor)
    return digest.hexdigest().upper()


def _gradient_sha256(model: nn.Module) -> tuple[str, list[str], list[str]]:
    digest = hashlib.sha256()
    missing: list[str] = []
    nonfinite: list[str] = []
    for name, parameter in model.named_parameters():
        if parameter.grad is None:
            missing.append(name)
            continue
        if not torch.isfinite(parameter.grad).all().item():
            nonfinite.append(name)
        _update_tensor_hash(digest, name, parameter.grad)
    return digest.hexdigest().upper(), missing, nonfinite


def _worker(mode: str) -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; no determinism diagnostic ran.")
    if mode == "deterministic_candidate":
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.conv.fp32_precision = "ieee"
        torch.backends.cuda.matmul.fp32_precision = "ieee"
    elif mode != "ambient_defaults":
        raise ValueError(f"Unsupported worker mode: {mode}")

    device = torch.device("cuda:0")
    model = build_formal_model(test_seed=MODEL_TEST_SEED)
    initial_state_hash = state_dict_sha256(model)
    model.to(device).train()
    inputs = torch.randn(
        4,
        3,
        32,
        32,
        generator=torch.Generator().manual_seed(INPUT_TEST_SEED),
    ).to(device)
    targets = torch.tensor([0, 1, 2, 3], dtype=torch.long, device=device)

    logits = model(inputs)
    loss = nn.functional.cross_entropy(logits, targets)
    loss.backward()
    torch.cuda.synchronize(device)
    gradient_hash, missing, nonfinite = _gradient_sha256(model)
    if not torch.isfinite(loss).item() or missing or nonfinite:
        raise RuntimeError(
            f"Invalid worker result: finite_loss={torch.isfinite(loss).item()}, "
            f"missing={missing}, nonfinite={nonfinite}"
        )

    print(
        json.dumps(
            {
                "mode": mode,
                "initial_state_sha256": initial_state_hash,
                "post_forward_state_sha256": state_dict_sha256(model),
                "logits_sha256": _tensor_sha256("logits", logits),
                "loss": float(loss.detach().cpu().item()),
                "gradient_sha256": gradient_hash,
                "trainable_gradient_tensors": sum(
                    parameter.grad is not None for parameter in model.parameters()
                ),
                "settings": {
                    "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
                    "deterministic_algorithms": (
                        torch.are_deterministic_algorithms_enabled()
                    ),
                    "cudnn_deterministic": torch.backends.cudnn.deterministic,
                    "cudnn_benchmark": torch.backends.cudnn.benchmark,
                    "cudnn_convolution_fp32_precision": (
                        torch.backends.cudnn.conv.fp32_precision
                    ),
                    "matmul_fp32_precision": (
                        torch.backends.cuda.matmul.fp32_precision
                    ),
                    "cublas_workspace_config": os.environ.get(
                        "CUBLAS_WORKSPACE_CONFIG"
                    ),
                },
            },
            sort_keys=True,
        )
    )


def _run_fresh_worker(mode: str) -> dict[str, object]:
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = "0"
    if mode == "deterministic_candidate":
        environment["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    else:
        environment.pop("CUBLAS_WORKSPACE_CONFIG", None)
    completed = subprocess.run(
        [
            sys.executable,
            "-X",
            "dev",
            "-W",
            "error",
            str(Path(__file__).resolve()),
            "--worker",
            mode,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return json.loads(completed.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--worker",
        choices=("ambient_defaults", "deterministic_candidate"),
    )
    arguments = parser.parse_args()
    if arguments.worker is not None:
        _worker(arguments.worker)
        return

    runs = {
        mode: [_run_fresh_worker(mode) for _ in range(RUNS_PER_MODE)]
        for mode in ("ambient_defaults", "deterministic_candidate")
    }
    properties = torch.cuda.get_device_properties(0)
    report = {
        "classification": "PHASE1-DETERMINISM-DIAGNOSTIC-ONLY",
        "evidence_class": "DERIVED",
        "record_date": datetime.now().astimezone().date().isoformat(),
        "optimizer_constructed": False,
        "optimizer_steps": 0,
        "fresh_processes_per_mode": RUNS_PER_MODE,
        "model_test_seed": MODEL_TEST_SEED,
        "input_test_seed": INPUT_TEST_SEED,
        "input_shape": [4, 3, 32, 32],
        "execution_environment": {
            "python": sys.version,
            "torch": torch.__version__,
            "torch_cuda_runtime": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
            "device": properties.name,
            "compute_capability": f"{properties.major}.{properties.minor}",
            "worker_python_hash_seed": "0",
        },
        "runs": runs,
        "unique_gradient_hashes": {
            mode: len({run["gradient_sha256"] for run in mode_runs})
            for mode, mode_runs in runs.items()
        },
        "deterministic_candidate_bit_exact": all(
            len({run[field] for run in runs["deterministic_candidate"]}) == 1
            for field in (
                "initial_state_sha256",
                "post_forward_state_sha256",
                "logits_sha256",
                "loss",
                "gradient_sha256",
            )
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
