from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_deterministic_gpu_checkpoint_replay_report_is_exact_and_nonformal() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "phase3_synthetic_mechanics_diagnostic.py"),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    report = json.loads(completed.stdout.decode("utf-8"))
    assert report["classification"] == "NON-FORMAL-SYNTHETIC-OPTIMIZER-MECHANICS"
    assert report["evidence_class"] == "DERIVED"
    assert report["scope"] == {
        "accuracy_computations": 0,
        "cifar_samples_read": 0,
        "formal_optimizer_steps": 0,
        "predictions_computed": 0,
        "pretrained_downloads": 0,
        "synthetic_optimizer_calls_executed": 5,
        "synthetic_steps_per_compared_trajectory": 3,
    }
    assert report["replay"]["losses_bit_exact"] is True
    assert report["replay"]["model_state_bit_exact"] is True
    assert report["replay"]["optimizer_state_bit_exact"] is True
    assert report["runtime"]["deterministic_algorithms"] is True
    assert report["runtime"]["cudnn_benchmark"] is False
    assert report["runtime"]["cudnn_deterministic"] is True
    assert report["runtime"]["cudnn_convolution_fp32_precision"] == "ieee"
    assert report["runtime"]["matmul_fp32_precision"] == "ieee"
    assert report["runtime"]["cublas_workspace_config"] == ":4096:8"
    assert report["runtime"]["amp_used"] is False
    assert report["runtime"]["compile_used"] is False
    assert report["runtime"]["recomputation_used"] is False
    assert report["runtime"]["runtime_rngs_initialized_from_approved_bundle"] is True
