from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = PROJECT_ROOT / "evidence"


def _run_json_script(name: str) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-X", "dev", "-W", "error", str(PROJECT_ROOT / "scripts" / name)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def test_locked_toronto_artifacts_replay_full_semantic_evidence() -> None:
    lock = json.loads((EVIDENCE / "cifar10-artifacts.json").read_text("utf-8"))
    stored = json.loads(
        (EVIDENCE / "phase2_cifar10_artifact_diagnostic_2026-08-16.json").read_text(
            "utf-8"
        )
    )
    live = _run_json_script("phase2_verify_cifar10_artifacts.py")

    assert lock["classification"] == "PHASE2-CIFAR10-APPROVED-ARTIFACT-LOCK"
    assert lock["selection_decision_date"] == "2026-08-23"
    assert lock["formal_dataset_selected"] is True
    assert lock["artifacts"]["toronto_binary"]["approved"] is True
    assert lock["artifacts"]["toronto_python"]["approved"] is False
    assert stored["project_git"] == {
        "commit": "b2cd18b4a5d8e8166426da42649e1e318d7e1d44",
        "worktree_clean_before_output": True,
    }
    for field in (
        "classification",
        "evidence_class",
        "optimizer_constructed",
        "optimizer_steps",
        "accuracy_computed",
        "batches",
        "splits",
        "semantic_equivalence",
        "historical_torch7_archive",
    ):
        assert live[field] == stored[field], field
    for artifact in ("toronto_python", "toronto_binary"):
        assert {
            key: value
            for key, value in live["artifacts"][artifact].items()
            if key != "path"
        } == {
            key: value
            for key, value in stored["artifacts"][artifact].items()
            if key != "path"
        }
    assert stored["semantic_equivalence"][
        "all_60000_labels_and_images_byte_exact"
    ] is True
    assert stored["splits"]["train"]["class_histogram"] == [5_000] * 10
    assert stored["splits"]["test"]["class_histogram"] == [1_000] * 10


def test_complete_candidate_epoch_replays_exactly_across_worker_counts() -> None:
    stored = json.loads(
        (EVIDENCE / "phase2_data_pipeline_diagnostic_2026-08-16.json").read_text(
            "utf-8"
        )
    )
    live = _run_json_script("phase2_data_pipeline_diagnostic.py")

    assert stored["project_git"] == {
        "commit": "5409943f8611d1020befde8e38422952eade12a5",
        "worktree_clean_before_output": True,
    }
    for field in (
        "classification",
        "evidence_class",
        "model_constructed",
        "optimizer_constructed",
        "optimizer_steps",
        "accuracy_computed",
        "candidate_h003_mapping",
        "train_zero_workers",
        "train_two_workers",
        "worker_count_bit_exact",
        "test_normalization_only_zero_workers",
    ):
        assert live[field] == stored[field], field
    assert {
        key: value for key, value in live["artifact"].items() if key != "path"
    } == {
        key: value for key, value in stored["artifact"].items() if key != "path"
    }
    assert live["prepared_manifest"]["sha256"] == stored["prepared_manifest"][
        "sha256"
    ]
    # The dated diagnostic preserves its pre-approval state. D-010 records the
    # later human approval without rewriting the original evidence output.
    assert stored["candidate_h003_mapping"]["approved"] is False
    assert stored["worker_count_bit_exact"] is True
    assert stored["train_zero_workers"]["batches"] == 782
    assert stored["train_zero_workers"]["last_batch_size"] == 16
    assert stored["test_normalization_only_zero_workers"]["batches"] == 157
    assert stored["test_normalization_only_zero_workers"]["last_batch_size"] == 16
