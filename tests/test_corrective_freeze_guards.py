from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import densenet_reproduction.data as data_module
from densenet_reproduction.formal_checkpoint import FormalCheckpointProvenance
from densenet_reproduction.formal_training import (
    FormalTrainingRequest,
    _require_initial_boundary_resume_state,
    _validate_training_progress,
    run_formal_training_seed,
)
from densenet_reproduction.phase5 import (
    AppendOnlyAttemptLedger,
    LaunchIdentity,
    Phase6Authorization,
    canonical_json_bytes,
    sha256_bytes,
    verify_phase6_decision_artifacts,
)


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
        gpu_name="NVIDIA GeForce RTX 3070 Ti",
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


def _verified_authorization(tmp_path: Path) -> Phase6Authorization:
    common = {
        "approval_commit": "a" * 40,
        "approved": True,
        "classification": "FORMAL-GOVERNANCE-DECISION-V1",
        "evidence_class": "IMPLEMENTATION-ASSUMPTION",
        "formal_optimizer_steps_at_approval": 0,
        "freeze_manifest_sha256": "A" * 64,
        "schema_version": 1,
    }
    phase5 = tmp_path / "phase5.json"
    phase6 = tmp_path / "phase6.json"
    phase5.write_bytes(
        canonical_json_bytes(
            {
                **common,
                "decision_id": "D-023",
                "decision_kind": "formal-freeze-completion",
            }
        )
    )
    phase6.write_bytes(
        canonical_json_bytes(
            {**common, "decision_id": "D-024", "decision_kind": "phase6-entry"}
        )
    )
    authorization = Phase6Authorization(
        "A" * 64,
        sha256_bytes(phase5.read_bytes()),
        sha256_bytes(phase6.read_bytes()),
    )
    verify_phase6_decision_artifacts(
        authorization,
        expected_freeze_manifest_sha256="A" * 64,
        phase5_completion_decision_path=phase5,
        phase6_entry_decision_path=phase6,
    )
    return authorization


def _prepared_train_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    monkeypatch.setattr(data_module, "CIFAR10_BINARY_BATCH_BYTES", 4)
    prepared = tmp_path / "prepared"
    prepared.mkdir(exist_ok=True)
    files: dict[str, dict[str, object]] = {}
    for index in range(1, 6):
        name = f"data_batch_{index}.bin"
        payload = bytes([index]) * 4
        (prepared / name).write_bytes(payload)
        files[name] = {
            "bytes": 4,
            "sha256": hashlib.sha256(payload).hexdigest().upper(),
        }
    files["test_batch.bin"] = {"bytes": 4, "sha256": "A" * 64}
    (prepared / "prepared-manifest.json").write_text(
        json.dumps(
            {
                "classification": "PHASE2-DERIVED-DATA-CACHE-NOT-FORMAL-FREEZE",
                "files": files,
                "source_archive": {
                    "bytes": 1,
                    "filename": "cifar-10-binary.tar.gz",
                    "md5": "0" * 32,
                    "sha256": "D" * 64,
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return prepared


def _progress_record(ledger: AppendOnlyAttemptLedger) -> dict[str, object]:
    return {
        "accepted_step": 1,
        "batch_index": 0,
        "classification": "FORMAL-TRAINING-PROGRESS-V1",
        "epoch": 1,
        "ledger_head_sha256": ledger.records[-1]["record_sha256"],
        "loss_fp32_decimal": "2.5",
        "master_seed": 1021082110,
        "physical_completed_calls": 1,
    }


def test_initial_boundary_state_preserves_completed_ledger_and_rejects_checkpoint(
    tmp_path: Path,
) -> None:
    ledger = AppendOnlyAttemptLedger(tmp_path / "optimizer-attempts.jsonl", create=True)
    intent = ledger.append_intent(
        master_seed=1021082110, epoch=1, batch_index=0, accepted_step=1
    )
    ledger.append_completion(intent)
    progress = tmp_path / "training-progress.jsonl"
    progress.write_bytes(canonical_json_bytes(_progress_record(ledger)))
    _validate_training_progress(progress, master_seed=1021082110, ledger=ledger)
    _require_initial_boundary_resume_state(
        tmp_path, master_seed=1021082110, ledger=ledger
    )
    (tmp_path / "epoch-001.pt").write_bytes(b"reserved-after-crash")
    with pytest.raises(RuntimeError, match="checkpoint artifact"):
        _require_initial_boundary_resume_state(
            tmp_path, master_seed=1021082110, ledger=ledger
        )


def test_initial_boundary_rejects_unresolved_intent_before_model_or_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_root = tmp_path / ("A" * 64) / "seed-1021082110"
    run_root.mkdir(parents=True)
    ledger = AppendOnlyAttemptLedger(
        run_root / "optimizer-attempts.jsonl", create=True
    )
    ledger.append_intent(
        master_seed=1021082110, epoch=1, batch_index=0, accepted_step=1
    )
    (run_root / "training-progress.jsonl").write_bytes(b"")
    monkeypatch.setattr(
        "densenet_reproduction.formal_training.build_project_seeded_model",
        lambda seed: (_ for _ in ()).throw(AssertionError("model constructed")),
    )
    monkeypatch.setattr(
        "densenet_reproduction.formal_training.Cifar10BinaryDataset",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("data constructed")),
    )
    launch = _launch()
    with pytest.raises(RuntimeError, match="Unresolved optimizer intent"):
        run_formal_training_seed(
            FormalTrainingRequest(
                prepared_directory=_prepared_train_directory(tmp_path, monkeypatch),
                run_directory=run_root,
                master_seed=1021082110,
                device_index=0,
                authorization=_verified_authorization(tmp_path),
                expected_launch=launch,
                observed_launch=launch,
                base_provenance=FormalCheckpointProvenance(
                    freeze_manifest_sha256="A" * 64,
                    source_commit="b" * 40,
                    project_wheel_sha256="E" * 64,
                    environment_manifest_sha256="1" * 64,
                    dataset_sha256="D" * 64,
                    config_sha256="C" * 64,
                    ledger_head_sha256="0" * 64,
                ),
                resume_initial_boundary=True,
            )
        )


def test_clean_initial_boundary_reaches_only_mock_model_factory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_root = tmp_path / ("A" * 64) / "seed-1021082110"
    run_root.mkdir(parents=True)
    ledger = AppendOnlyAttemptLedger(
        run_root / "optimizer-attempts.jsonl", create=True
    )
    intent = ledger.append_intent(
        master_seed=1021082110, epoch=1, batch_index=0, accepted_step=1
    )
    ledger.append_completion(intent)
    (run_root / "training-progress.jsonl").write_bytes(
        canonical_json_bytes(_progress_record(ledger))
    )

    class ReachedMockModelFactory(RuntimeError):
        pass

    monkeypatch.setattr(
        "densenet_reproduction.formal_training.build_project_seeded_model",
        lambda seed: (_ for _ in ()).throw(ReachedMockModelFactory("mock reached")),
    )
    monkeypatch.setattr(
        "densenet_reproduction.formal_training.enforce_formal_runtime_policy",
        lambda device_index: "mock-device",
    )
    launch = _launch()
    with pytest.raises(ReachedMockModelFactory, match="mock reached"):
        run_formal_training_seed(
            FormalTrainingRequest(
                prepared_directory=_prepared_train_directory(tmp_path, monkeypatch),
                run_directory=run_root,
                master_seed=1021082110,
                device_index=0,
                authorization=_verified_authorization(tmp_path),
                expected_launch=launch,
                observed_launch=launch,
                base_provenance=FormalCheckpointProvenance(
                    freeze_manifest_sha256="A" * 64,
                    source_commit="b" * 40,
                    project_wheel_sha256="E" * 64,
                    environment_manifest_sha256="1" * 64,
                    dataset_sha256="D" * 64,
                    config_sha256="C" * 64,
                    ledger_head_sha256="0" * 64,
                ),
                resume_initial_boundary=True,
            )
        )


def test_direct_training_api_rejects_second_seed_before_model_or_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_root = tmp_path / ("A" * 64) / "seed-1747066946"
    run_root.mkdir(parents=True)
    monkeypatch.setattr(
        "densenet_reproduction.formal_training.build_project_seeded_model",
        lambda seed: (_ for _ in ()).throw(AssertionError("model constructed")),
    )
    monkeypatch.setattr(
        "densenet_reproduction.formal_training.Cifar10BinaryDataset",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("data constructed")),
    )
    launch = _launch()
    with pytest.raises(RuntimeError, match="Earlier formal seed"):
        run_formal_training_seed(
            FormalTrainingRequest(
                prepared_directory=_prepared_train_directory(tmp_path, monkeypatch),
                run_directory=run_root,
                master_seed=1747066946,
                device_index=0,
                authorization=_verified_authorization(tmp_path),
                expected_launch=launch,
                observed_launch=launch,
                base_provenance=FormalCheckpointProvenance(
                    freeze_manifest_sha256="A" * 64,
                    source_commit="b" * 40,
                    project_wheel_sha256="E" * 64,
                    environment_manifest_sha256="1" * 64,
                    dataset_sha256="D" * 64,
                    config_sha256="C" * 64,
                    ledger_head_sha256="0" * 64,
                ),
            )
        )


@pytest.mark.parametrize(
    "mutation, message",
    [
        ({"accepted_step": 2}, "inconsistent"),
        ({"loss_fp32_decimal": "nan"}, "non-finite"),
        ({"master_seed": 1747066946}, "inconsistent"),
    ],
)
def test_training_progress_mutations_fail_closed(
    tmp_path: Path, mutation: dict[str, object], message: str
) -> None:
    ledger = AppendOnlyAttemptLedger(tmp_path / "ledger.jsonl", create=True)
    intent = ledger.append_intent(
        master_seed=1021082110, epoch=1, batch_index=0, accepted_step=1
    )
    ledger.append_completion(intent)
    record = {**_progress_record(ledger), **mutation}
    path = tmp_path / "progress.jsonl"
    path.write_bytes(canonical_json_bytes(record))
    with pytest.raises(ValueError, match=message):
        _validate_training_progress(path, master_seed=1021082110, ledger=ledger)


def test_training_progress_cannot_claim_an_intent_as_completed_head(
    tmp_path: Path,
) -> None:
    ledger = AppendOnlyAttemptLedger(tmp_path / "ledger.jsonl", create=True)
    intent = ledger.append_intent(
        master_seed=1021082110, epoch=1, batch_index=0, accepted_step=1
    )
    ledger.append_completion(intent)
    record = {
        **_progress_record(ledger),
        "ledger_head_sha256": ledger.records[0]["record_sha256"],
    }
    path = tmp_path / "progress.jsonl"
    path.write_bytes(canonical_json_bytes(record))
    with pytest.raises(ValueError, match="inconsistent"):
        _validate_training_progress(path, master_seed=1021082110, ledger=ledger)
