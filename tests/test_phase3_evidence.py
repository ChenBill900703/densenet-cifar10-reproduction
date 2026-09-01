from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "evidence" / "phase3_synthetic_mechanics_2026-08-23.json"
HEX64 = re.compile(r"^[0-9A-F]{64}$")


def test_phase3_machine_report_is_strictly_scoped_and_hash_shaped() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report["classification"] == "NON-FORMAL-SYNTHETIC-OPTIMIZER-MECHANICS"
    assert report["evidence_class"] == "DERIVED"
    assert report["record_date"] == "2026-08-23"
    assert report["scope"] == {
        "accuracy_computations": 0,
        "cifar_samples_read": 0,
        "formal_optimizer_steps": 0,
        "predictions_computed": 0,
        "pretrained_downloads": 0,
        "synthetic_optimizer_calls_executed": 5,
        "synthetic_steps_per_compared_trajectory": 3,
    }
    assert report["runtime"]["runtime_rngs_initialized_from_approved_bundle"] is True
    assert all(
        report["replay"][name] is True
        for name in (
            "losses_bit_exact",
            "model_state_bit_exact",
            "optimizer_state_bit_exact",
        )
    )
    assert HEX64.fullmatch(report["replay"]["checkpoint_sha256"])
    assert HEX64.fullmatch(report["replay"]["final_model_state_sha256"])
    assert all(
        HEX64.fullmatch(value)
        for name, value in report["provenance"].items()
        if name != "source_commit"
    )
    assert re.fullmatch(r"[0-9a-f]{40}", report["provenance"]["source_commit"])


def test_phase3_report_source_commit_exists_and_is_ancestor_of_head() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    source_commit = report["provenance"]["source_commit"]
    subprocess.run(
        ["git", "cat-file", "-e", f"{source_commit}^{{commit}}"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
