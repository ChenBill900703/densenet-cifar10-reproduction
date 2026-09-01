from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess

from densenet_reproduction import validate_success_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "evidence" / "phase4_exact_device_2026-08-23.json"
CONFIG_PATH = PROJECT_ROOT / "docs" / "phase4_entry_decision_proposal.md"
ENVIRONMENT_LOCK = PROJECT_ROOT / "requirements" / "environment-lock.txt"
REPORT_SHA256 = "7B22E8B5E97F7BFED961C1CC12F9F4E8A6BF56D9680A147CBC83910E66FAE906"
SOURCE_COMMIT = "f91cdf6ee5e8fafd20148af3313b3a56a16e6747"
HEX64 = re.compile(r"^[0-9A-F]{64}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _report() -> dict[str, object]:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_phase4_report_bytes_and_provenance_are_exact() -> None:
    report = _report()
    assert _sha256(REPORT_PATH) == REPORT_SHA256
    assert report["record_date"] == "2026-08-23"
    provenance = report["provenance"]
    assert provenance["source_commit"] == SOURCE_COMMIT
    assert provenance["environment_lock_sha256"] == _sha256(ENVIRONMENT_LOCK)
    assert provenance["phase4_config_sha256"] == _sha256(CONFIG_PATH)
    assert provenance["dataset_sha256"] == (
        "C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD"
    )
    validate_success_report(
        report,
        expected_source_commit=SOURCE_COMMIT,
        expected_environment_lock_sha256=_sha256(ENVIRONMENT_LOCK),
        expected_config_sha256=_sha256(CONFIG_PATH),
    )


def test_phase4_source_commit_exists_is_ancestor_and_contains_diagnostic() -> None:
    subprocess.run(
        ["git", "cat-file", "-e", f"{SOURCE_COMMIT}^{{commit}}"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", SOURCE_COMMIT, "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    committed_script = subprocess.run(
        ["git", "show", f"{SOURCE_COMMIT}:scripts/phase4_exact_device_diagnostic.py"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert hashlib.sha256(committed_script).digest()
    assert b"PHASE4_TOTAL_SYNTHETIC_CALLS" not in committed_script
    assert b"worker_a[\"actual_optimizer_calls\"] == 11" in committed_script
    assert b"worker_b[\"actual_optimizer_calls\"] == 5" in committed_script


def test_phase4_memory_and_timing_aggregates_recompute_exactly() -> None:
    report = _report()
    records = list(report["memory_records"].values())
    assert len(records) == 66
    assert max(record["peak_allocated_bytes"] for record in records) == 2_336_236_544
    assert max(record["peak_reserved_bytes"] for record in records) == 2_680_160_256
    assert min(record["free_bytes"] for record in records) == 4_652_531_712
    assert report["memory_records"]["worker_a_before_model"]["free_bytes"] == 7_435_452_416
    timings = report["synthetic"]["measured_update_seconds"]
    assert len(timings) == 10
    summary = report["synthetic"]["timing_summary_seconds"]
    assert summary == {
        "arithmetic_mean": statistics.fmean(timings),
        "median": statistics.median(timings),
        "minimum": min(timings),
        "maximum": max(timings),
    }
    assert report["synthetic"][
        "generated_kernel_projection_seconds_excluding_dataloader_evaluation_checkpoint_and_contention"
    ] == statistics.fmean(timings) * 234_600


def test_phase4_replay_hashes_and_cifar_forward_are_strictly_scoped() -> None:
    report = _report()
    assert all(report["replay"].values())
    assert report["scope"] == {
        "accuracy_or_error_computations": 0,
        "cifar_backward_calls": 0,
        "cifar_forward_calls": 1,
        "cifar_loss_calls": 0,
        "cifar_optimizer_calls": 0,
        "cifar_samples_read": 64,
        "formal_optimizer_steps": 0,
        "predictions_or_argmax": 0,
        "pretrained_downloads": 0,
        "synthetic_optimizer_calls": 16,
        "validation_or_test_samples": 0,
    }
    assert report["synthetic"]["worker_a_calls"] == 11
    assert report["synthetic"]["worker_b_calls"] == 5
    assert report["synthetic"]["gradient_tensors"] == 299
    assert report["synthetic"]["momentum_state_tensors"] == 299
    assert report["cifar_forward"]["artifact"]["sha256"] == report["provenance"]["dataset_sha256"]
    assert report["cifar_forward"]["request_count"] == 64
    assert report["cifar_forward"]["workers"] == 2
    assert report["cifar_forward"]["logits_shape"] == [64, 10]
    assert report["cifar_forward"]["bn_counters_advanced"] == 99
    for value in (
        report["synthetic"]["checkpoint_sha256"],
        report["synthetic"]["final_model_state_sha256"],
        report["synthetic"]["final_optimizer_state_sha256"],
        report["cifar_forward"]["inputs_sha256"],
        report["cifar_forward"]["targets_sha256"],
        report["cifar_forward"]["logits_sha256"],
        report["cifar_forward"]["model_state_sha256_after_forward"],
    ):
        assert HEX64.fullmatch(value)
