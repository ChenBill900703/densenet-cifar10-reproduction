from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from densenet_reproduction.phase5 import (
    AppendOnlyAttemptLedger,
    ArtifactIdentity,
    LaunchIdentity,
    PHASE5_PROJECT_SEEDS,
    Phase6Authorization,
    build_artifact_identities,
    canonical_json_bytes,
    expected_aggregate_fields,
    expected_formal_config,
    required_storage_bytes,
    sha256_bytes,
    validate_aggregate_result,
    validate_formal_config,
    validate_freeze_manifest,
    validate_launch_identity,
    validate_seed_result,
    validate_stage_sequence,
    require_phase6_authorization,
    verify_phase6_decision_artifacts,
    verify_artifact_identities,
    verify_attempt_records,
)
from densenet_reproduction.phase5_launch import expected_launch_identity


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_committed_formal_config_is_exact_canonical_approved_candidate() -> None:
    path = PROJECT_ROOT / "config" / "formal_config.json"
    document = validate_formal_config(path)
    assert document == expected_formal_config()
    assert path.read_bytes() == canonical_json_bytes(document)
    assert sha256_bytes(path.read_bytes()) == sha256_bytes(canonical_json_bytes(document))


def test_formal_config_rejects_noncanonical_and_semantic_mutation(tmp_path: Path) -> None:
    noncanonical = tmp_path / "pretty.json"
    noncanonical.write_text(json.dumps(expected_formal_config(), indent=2), encoding="ascii")
    with pytest.raises(ValueError, match="canonical"):
        validate_formal_config(noncanonical)
    mutated = expected_formal_config()
    mutated["model"]["batch_size"] = 32
    path = tmp_path / "mutated.json"
    path.write_bytes(canonical_json_bytes(mutated))
    with pytest.raises(ValueError, match="approved"):
        validate_formal_config(path)


def test_artifact_tree_exact_identity_and_mutation_detection(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "a.whl").write_bytes(b"wheel-a")
    (tmp_path / "nested" / "b.whl").write_bytes(b"wheel-b")
    identities = build_artifact_identities(tmp_path)
    assert [item.path for item in identities] == ["a.whl", "nested/b.whl"]
    verify_artifact_identities(tmp_path, identities)
    (tmp_path / "a.whl").write_bytes(b"wheel-A")
    with pytest.raises(ValueError, match="exactly"):
        verify_artifact_identities(tmp_path, identities)


@pytest.mark.parametrize("unsafe", ["../x", "/x", "a\\b", "./x", "a//../b"])
def test_artifact_identity_rejects_unsafe_paths(unsafe: str) -> None:
    with pytest.raises(ValueError):
        ArtifactIdentity(unsafe, 1, "A" * 64)


def test_attempt_ledger_clean_and_crash_window_accounting(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    ledger = AppendOnlyAttemptLedger(path, create=True)
    first = ledger.append_intent(
        master_seed=PHASE5_PROJECT_SEEDS[0], epoch=1, batch_index=0, accepted_step=1
    )
    ledger.append_completion(first)
    ledger.append_intent(
        master_seed=PHASE5_PROJECT_SEEDS[0], epoch=1, batch_index=1, accepted_step=2
    )
    summary = ledger.summary()
    assert summary.intents == 2
    assert summary.completed_calls == 1
    assert summary.unresolved_intents == 1
    assert summary.physical_call_lower_bound == 1
    assert summary.physical_call_upper_bound == 2
    reopened = AppendOnlyAttemptLedger(path, create=False)
    assert reopened.summary() == summary
    assert len(path.read_bytes().splitlines()) == 3


def test_attempt_ledger_rejects_tamper_truncation_duplicate_and_bad_completion(
    tmp_path: Path,
) -> None:
    path = tmp_path / "attempts.jsonl"
    ledger = AppendOnlyAttemptLedger(path, create=True)
    intent = ledger.append_intent(
        master_seed=PHASE5_PROJECT_SEEDS[0], epoch=1, batch_index=0, accepted_step=1
    )
    with pytest.raises(FileExistsError):
        AppendOnlyAttemptLedger(path, create=True)
    with pytest.raises(ValueError, match="pending"):
        ledger.append_completion("A" * 64)
    ledger.append_completion(intent)
    records = list(ledger.records)
    records[0]["batch_index"] = 2
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_attempt_records(records)
    path.write_bytes(path.read_bytes()[:-1])
    with pytest.raises(ValueError, match="torn"):
        AppendOnlyAttemptLedger(path, create=False)


def _complete_stage_events() -> list[dict[str, int | str]]:
    events = [
        {
            "event": "training-complete",
            "master_seed": seed,
            "checkpoint_epoch": 300,
            "test_records": 0,
        }
        for seed in PHASE5_PROJECT_SEEDS
    ]
    events.extend(
        {
            "event": "test-complete",
            "master_seed": seed,
            "checkpoint_epoch": 300,
            "test_records": 10000,
        }
        for seed in PHASE5_PROJECT_SEEDS
    )
    return events


def test_stage_sequence_requires_all_training_before_any_test() -> None:
    events = _complete_stage_events()
    validate_stage_sequence(events)
    early_test = list(events)
    early_test[1], early_test[3] = early_test[3], early_test[1]
    with pytest.raises(ValueError, match="train-all-then-test"):
        validate_stage_sequence(early_test)
    with pytest.raises(ValueError, match="train-all-then-test"):
        validate_stage_sequence(events[:-1])


def test_result_schemas_are_integer_primary_and_reject_predictions_or_selection() -> None:
    freeze_hash = "A" * 64
    seed_result = {
        "checkpoint_epoch": 300,
        "classification": "FORMAL-FINAL-TEST-RESULT-V1",
        "freeze_manifest_sha256": freeze_hash,
        "incorrect_count": 451,
        "master_seed": PHASE5_PROJECT_SEEDS[0],
        "test_attempts": 1,
        "test_records": 10000,
    }
    validate_seed_result(seed_result)
    with pytest.raises(ValueError, match="schema"):
        validate_seed_result({**seed_result, "predictions": [0]})

    calculated = expected_aggregate_fields([451, 462, 447])
    aggregate = {
        "classification": "FORMAL-AGGREGATE-RESULT-V1",
        "freeze_manifest_sha256": freeze_hash,
        "seeds": list(PHASE5_PROJECT_SEEDS),
        "selection": "none",
        **calculated,
    }
    validate_aggregate_result(aggregate)
    with pytest.raises(ValueError, match="selection"):
        validate_aggregate_result({**aggregate, "selection": "best"})


def _launch() -> LaunchIdentity:
    return LaunchIdentity(
        freeze_manifest_sha256="A" * 64,
        source_commit="b" * 40,
        config_sha256="C" * 64,
        dataset_sha256="D" * 64,
        project_wheel_sha256="E" * 64,
        python_runtime_sha256="F" * 64,
        environment_manifest_sha256="1" * 64,
        execution_account="REDACTED_DOMAIN\\REDACTED_ACCOUNT",
        execution_sid="<REDACTED_EXECUTION_SID>",
        windows_build="26100",
        python_build="3.12.13-test",
        driver_version="591.86",
        gpu_name="NVIDIA GeForce RTX 3070 Ti Laptop GPU",
        gpu_uuid="GPU-test",
        compute_capability="8.6",
        deterministic_algorithms=True,
        cudnn_benchmark=False,
        cudnn_deterministic=True,
        convolution_precision="ieee",
        matmul_precision="ieee",
        amp_enabled=False,
        compile_enabled=False,
    )


def test_launch_identity_matches_every_field_and_fails_closed() -> None:
    expected = _launch()
    validate_launch_identity(expected, expected)
    with pytest.raises(RuntimeError, match="driver_version"):
        validate_launch_identity(expected, replace(expected, driver_version="other"))
    with pytest.raises(RuntimeError, match="execution_account"):
        validate_launch_identity(
            expected, replace(expected, execution_account="<REDACTED_HOST>\\Other")
        )
    with pytest.raises(RuntimeError, match="execution_sid"):
        validate_launch_identity(expected, replace(expected, execution_sid="<REDACTED_TEST_SID>"))
    unsafe = replace(expected, deterministic_algorithms=False)
    with pytest.raises(RuntimeError):
        validate_launch_identity(unsafe, unsafe)


def test_storage_gate_uses_900_checkpoints_and_twenty_percent_headroom() -> None:
    assert required_storage_bytes(1000) == 1_080_000
    with pytest.raises(ValueError):
        required_storage_bytes(0)


def _identity(path: str, marker: str, size: int = 1) -> dict[str, object]:
    digest = marker if len(marker) == 64 else marker * 64
    return {"path": path, "bytes": size, "sha256": digest}


def _freeze_manifest() -> dict[str, object]:
    return {
        "artifacts": {
            "offline_requirements": _identity("evidence/offline-requirements.txt", "0"),
            "primary_paper": _identity("docs/1608.06993v5.pdf", "1"),
            "project_wheel": _identity("wheelhouse/project.whl", "2"),
            "python_runtime_archive": _identity("runtime/python.zip", "3"),
            "python_runtime_manifest": _identity("evidence/runtime.json", "4"),
            "source_lock": _identity("evidence/source-lock.json", "5"),
            "wheelhouse_manifest": _identity("evidence/wheels.json", "6"),
        },
        "classification": "PHASE5-FREEZE-CANDIDATE-NOT-APPROVED",
        "config": _identity("config/formal_config.json", "7"),
        "dataset": _identity(
            "data/cifar-10-binary.tar.gz",
            "C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD",
        ),
        "environment": {
            "compute_capability": "8.6",
            "driver_version": "591.86",
            "execution_account": "REDACTED_DOMAIN\\REDACTED_ACCOUNT",
            "execution_sid": "<REDACTED_EXECUTION_SID>",
            "gpu_name": "NVIDIA GeForce RTX 3070 Ti Laptop GPU",
            "gpu_uuid": "GPU-test",
            "installed_manifest_sha256": "8" * 64,
            "python_build": "3.12.13-test",
            "windows_build": "26100",
        },
        "evidence_class": "DERIVED",
        "policies": {
            "attempt_ledger": "append-only-intent-completion-sha256-v1",
            "checkpoint_retention": "all-300-per-seed",
            "final_evaluation": "train-all-three-then-test-once-in-fixed-order",
            "formal_optimizer_steps_at_freeze": 0,
            "run_layout": "runs/formal/<FULL_FREEZE_MANIFEST_SHA256>/seed-<MASTER_SEED>",
        },
        "schema_version": 2,
        "source": {
            "freeze_record_commit": None,
            "freeze_source_commit": "a" * 40,
            "git_bundle_bytes": 1,
            "git_bundle_sha256": "9" * 64,
        },
        "storage": {
            "checkpoint_bytes": 1000,
            "free_bytes_observed": 2_000_000,
            "headroom_percent": 20,
            "required_bytes": 1_080_000,
        },
        "target_slug": "densenet-bc-100-12__cifar10-plus__fp32__b64__e300",
        "tests": {
            "fresh_offline_passed": True,
            "formal_optimizer_steps": 0,
            "new_phase5_optimizer_diagnostics": 0,
            "project_passed": True,
            "source_verifier_passed": True,
        },
    }


def test_freeze_manifest_schema_is_closed_and_storage_gated() -> None:
    manifest = _freeze_manifest()
    validate_freeze_manifest(manifest)
    legacy = json.loads(json.dumps(manifest))
    legacy["schema_version"] = 1
    del legacy["environment"]["execution_account"]
    del legacy["environment"]["execution_sid"]
    validate_freeze_manifest(legacy)
    with pytest.raises(RuntimeError, match="Legacy freeze manifest"):
        expected_launch_identity(legacy, "A" * 64)
    with pytest.raises(ValueError, match="schema"):
        validate_freeze_manifest({**manifest, "unexpected": None})
    insufficient = json.loads(json.dumps(manifest))
    insufficient["storage"]["free_bytes_observed"] = 1
    with pytest.raises(ValueError, match="not satisfied"):
        validate_freeze_manifest(insufficient)


def _decision_record(kind: str, freeze_hash: str, decision_id: str) -> dict[str, object]:
    return {
        "approval_commit": "a" * 40,
        "approved": True,
        "classification": "FORMAL-GOVERNANCE-DECISION-V1",
        "decision_id": decision_id,
        "decision_kind": kind,
        "evidence_class": "IMPLEMENTATION-ASSUMPTION",
        "formal_optimizer_steps_at_approval": 0,
        "freeze_manifest_sha256": freeze_hash,
        "schema_version": 1,
    }


def _verified_authorization(tmp_path: Path, freeze_hash: str) -> Phase6Authorization:
    phase5 = tmp_path / "phase5.json"
    phase6 = tmp_path / "phase6.json"
    phase5.write_bytes(
        canonical_json_bytes(
            _decision_record("formal-freeze-completion", freeze_hash, "D-023")
        )
    )
    phase6.write_bytes(
        canonical_json_bytes(_decision_record("phase6-entry", freeze_hash, "D-024"))
    )
    authorization = Phase6Authorization(
        freeze_hash,
        sha256_bytes(phase5.read_bytes()),
        sha256_bytes(phase6.read_bytes()),
    )
    verify_phase6_decision_artifacts(
        authorization,
        expected_freeze_manifest_sha256=freeze_hash,
        phase5_completion_decision_path=phase5,
        phase6_entry_decision_path=phase6,
    )
    return authorization


def test_phase6_authorization_requires_exact_decision_artifacts(tmp_path: Path) -> None:
    freeze_hash = "A" * 64
    with pytest.raises(PermissionError, match="absent"):
        require_phase6_authorization(None, expected_freeze_manifest_sha256=freeze_hash)
    authorization = Phase6Authorization(freeze_hash, "B" * 64, "C" * 64)
    with pytest.raises(PermissionError, match="not been hash-verified"):
        require_phase6_authorization(
            authorization, expected_freeze_manifest_sha256=freeze_hash
        )
    verified = _verified_authorization(tmp_path, freeze_hash)
    require_phase6_authorization(verified, expected_freeze_manifest_sha256=freeze_hash)
    with pytest.raises(PermissionError, match="different"):
        require_phase6_authorization(
            verified, expected_freeze_manifest_sha256="D" * 64
        )


def test_phase6_decision_artifacts_fail_closed_on_mutation_and_swap(
    tmp_path: Path,
) -> None:
    freeze_hash = "A" * 64
    phase5 = tmp_path / "phase5.json"
    phase6 = tmp_path / "phase6.json"
    phase5.write_bytes(
        canonical_json_bytes(
            _decision_record("formal-freeze-completion", freeze_hash, "D-023")
        )
    )
    phase6.write_bytes(
        canonical_json_bytes(_decision_record("phase6-entry", freeze_hash, "D-024"))
    )
    authorization = Phase6Authorization(
        freeze_hash,
        sha256_bytes(phase5.read_bytes()),
        sha256_bytes(phase6.read_bytes()),
    )
    with pytest.raises(ValueError, match="kind mismatch"):
        verify_phase6_decision_artifacts(
            authorization,
            expected_freeze_manifest_sha256=freeze_hash,
            phase5_completion_decision_path=phase6,
            phase6_entry_decision_path=phase5,
        )
    mutated = dict(_decision_record("phase6-entry", freeze_hash, "D-024"))
    mutated["approved"] = False
    phase6.write_bytes(canonical_json_bytes(mutated))
    with pytest.raises(PermissionError, match="not approved"):
        verify_phase6_decision_artifacts(
            authorization,
            expected_freeze_manifest_sha256=freeze_hash,
            phase5_completion_decision_path=phase5,
            phase6_entry_decision_path=phase6,
        )


def test_phase6_decision_artifacts_reject_wrong_hash_noncanonical_and_wrong_freeze(
    tmp_path: Path,
) -> None:
    freeze_hash = "A" * 64
    phase5 = tmp_path / "phase5.json"
    phase6 = tmp_path / "phase6.json"
    phase5.write_bytes(
        canonical_json_bytes(
            _decision_record("formal-freeze-completion", freeze_hash, "D-023")
        )
    )
    phase6.write_bytes(
        canonical_json_bytes(_decision_record("phase6-entry", freeze_hash, "D-024"))
    )
    wrong_hash = Phase6Authorization(freeze_hash, "B" * 64, "C" * 64)
    with pytest.raises(PermissionError, match="SHA256 mismatch"):
        verify_phase6_decision_artifacts(
            wrong_hash,
            expected_freeze_manifest_sha256=freeze_hash,
            phase5_completion_decision_path=phase5,
            phase6_entry_decision_path=phase6,
        )
    phase6.write_text(
        "{\n  \"approved\": true\n}\n", encoding="ascii", newline="\n"
    )
    with pytest.raises(ValueError, match="canonical"):
        verify_phase6_decision_artifacts(
            wrong_hash,
            expected_freeze_manifest_sha256=freeze_hash,
            phase5_completion_decision_path=phase5,
            phase6_entry_decision_path=phase6,
        )
    phase6.write_bytes(
        canonical_json_bytes(
            _decision_record("phase6-entry", "D" * 64, "D-024")
        )
    )
    with pytest.raises(PermissionError, match="different freeze"):
        verify_phase6_decision_artifacts(
            wrong_hash,
            expected_freeze_manifest_sha256=freeze_hash,
            phase5_completion_decision_path=phase5,
            phase6_entry_decision_path=phase6,
        )
