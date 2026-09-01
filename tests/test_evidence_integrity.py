from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_paper_source_files_and_nested_repositories_match_the_source_lock() -> None:
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "verify_sources.py")],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    report = json.loads(completed.stdout)
    assert report["classification"] == "EVIDENCE_SOURCE_LOCK_NOT_FORMAL_FREEZE"
    assert report["evidence_class"] == "DERIVED"
    assert report["ok"] is True
    assert report["errors"] == []
    assert report["repositories_verified"] == 5
    assert report["files_verified"] == 19
    assert all(
        repository["required_history_complete"]
        for repository in report["repositories"]
    )
    assert all(
        repository["required_commits_present"]
        for repository in report["repositories"]
    )
    assert all(
        repository["pin_is_ancestor_of_remote_head"]
        for repository in report["repositories"]
    )
    assert all(not repository["shallow"] for repository in report["repositories"])
    assert all(not repository["partial_clone"] for repository in report["repositories"])
    assert all(repository["missing_objects"] == 0 for repository in report["repositories"])

    determinism = json.loads(
        (PROJECT_ROOT / "evidence" / "phase1_determinism_diagnostic_2026-08-16.json")
        .read_text(encoding="utf-8")
    )
    assert determinism["classification"] == "PHASE1-DETERMINISM-DIAGNOSTIC-ONLY"
    assert determinism["evidence_class"] == "DERIVED"
    assert determinism["optimizer_constructed"] is False
    assert determinism["optimizer_steps"] == 0
    assert determinism["deterministic_candidate_bit_exact"] is True
    assert determinism["unique_gradient_hashes"] == {
        "ambient_defaults": 3,
        "deterministic_candidate": 1,
    }
    for mode, runs in determinism["runs"].items():
        assert len(runs) == 3
        assert all(run["mode"] == mode for run in runs)
        assert all(run["trainable_gradient_tensors"] == 299 for run in runs)
        assert all(len(run["gradient_sha256"]) == 64 for run in runs)
        expected_unique = 3 if mode == "ambient_defaults" else 1
        assert len({run["gradient_sha256"] for run in runs}) == expected_unique
    replay_fields = (
        "initial_state_sha256",
        "post_forward_state_sha256",
        "logits_sha256",
        "loss",
        "gradient_sha256",
    )
    recomputed_bit_exact = all(
        len(
            {
                run[field]
                for run in determinism["runs"]["deterministic_candidate"]
            }
        )
        == 1
        for field in replay_fields
    )
    assert determinism["deterministic_candidate_bit_exact"] is recomputed_bit_exact
    assert recomputed_bit_exact is True
    assert all(
        len({run[field] for run in determinism["runs"]["ambient_defaults"]}) == 1
        for field in replay_fields[:-1]
    )

    precision = json.loads(
        (PROJECT_ROOT / "evidence" / "phase1_precision_diagnostic_2026-08-16.json")
        .read_text(encoding="utf-8")
    )
    assert precision["classification"] == "PHASE1-PRECISION-DIAGNOSTIC-ONLY"
    assert precision["evidence_class"] == "DERIVED"
    assert precision["optimizer_constructed"] is False
    assert precision["optimizer_steps"] == 0
    assert precision["logit_elements_per_output"] == 30
    assert precision["compute_capability"] == "8.6"
    assert precision["observed_process_defaults"] == {
        "cudnn_convolution_fp32_precision": "tf32",
        "matmul_fp32_precision": "none",
        "deterministic_algorithms": False,
        "cudnn_enabled": True,
        "cudnn_benchmark": False,
        "cudnn_deterministic": False,
    }
    assert all(
        len(digest) == 64 for digest in precision["output_raw_sha256"].values()
    )
    for comparison in precision["comparisons"].values():
        assert comparison["relative_infinity_error"] == (
            comparison["max_absolute_error"] / comparison["denominator_used"]
        )

    stress = json.loads(
        (
            PROJECT_ROOT
            / "evidence"
            / "phase1_numerical_stress_observation_2026-08-16.json"
        ).read_text(encoding="utf-8")
    )
    assert stress["classification"] == (
        "PHASE1-ONE-TIME-INDEPENDENT-NUMERICAL-STRESS-OBSERVATION"
    )
    assert stress["evidence_class"] == "DERIVED"
    assert stress["replay_script_committed"] is False
    assert stress["optimizer_constructed"] is False
    assert stress["optimizer_steps"] == 0
    assert stress["dataset_examples_read"] == 0
