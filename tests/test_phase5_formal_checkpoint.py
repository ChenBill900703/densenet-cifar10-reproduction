from __future__ import annotations

import ast
from pathlib import Path

import pytest
import torch

from densenet_reproduction.formal_checkpoint import (
    FormalCheckpointProvenance,
    STRUCTURAL_FIXTURE_CLASSIFICATION,
    load_formal_checkpoint,
    save_formal_checkpoint,
    write_structural_checkpoint_size_fixture,
)
from densenet_reproduction.formal_runtime import (
    FormalStepCoordinates,
    execute_accounted_optimizer_call,
    require_create_new_formal_run_root,
    require_formal_seed_training_order,
)
from densenet_reproduction.phase5 import (
    AppendOnlyAttemptLedger,
    AttemptSummary,
    LaunchIdentity,
    Phase6Authorization,
    canonical_json_bytes,
    sha256_bytes,
    verify_phase6_decision_artifacts,
)
from densenet_reproduction import build_phase3_optimizer, build_project_seeded_model


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


def _verified_authorization(tmp_path: Path) -> Phase6Authorization:
    freeze_hash = "A" * 64
    common = {
        "approval_commit": "a" * 40,
        "approved": True,
        "classification": "FORMAL-GOVERNANCE-DECISION-V1",
        "evidence_class": "IMPLEMENTATION-ASSUMPTION",
        "formal_optimizer_steps_at_approval": 0,
        "freeze_manifest_sha256": freeze_hash,
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


def test_structural_checkpoint_fixture_has_full_momentum_without_any_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_step(*args: object, **kwargs: object) -> None:
        raise AssertionError("optimizer.step must not run in Phase 5 fixture")

    monkeypatch.setattr(torch.optim.SGD, "step", forbidden_step)
    path = tmp_path / "structural.pt"
    size = write_structural_checkpoint_size_fixture(path)
    payload = torch.load(path, map_location="cpu", weights_only=True)
    assert size == path.stat().st_size > 0
    assert payload["classification"] == STRUCTURAL_FIXTURE_CLASSIFICATION
    assert payload["provenance"]["not_a_formal_checkpoint"] is True
    assert payload["test_records_accessed"] == 0
    assert len(payload["optimizer_state"]["state"]) == 299
    assert all(
        set(entry) == {"momentum_buffer"}
        for entry in payload["optimizer_state"]["state"].values()
    )


def _structural_model_optimizer():
    model = build_project_seeded_model(1021082110)
    optimizer = build_phase3_optimizer(model, epoch=1)
    for parameter in model.parameters():
        if parameter.requires_grad:
            optimizer.state[parameter]["momentum_buffer"] = torch.zeros_like(parameter)
    return model, optimizer


def _provenance() -> FormalCheckpointProvenance:
    return FormalCheckpointProvenance(
        freeze_manifest_sha256="A" * 64,
        source_commit="b" * 40,
        project_wheel_sha256="C" * 64,
        environment_manifest_sha256="D" * 64,
        dataset_sha256="E" * 64,
        config_sha256="F" * 64,
        ledger_head_sha256="1" * 64,
    )


def test_formal_checkpoint_mock_round_trip_without_optimizer_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        torch.optim.SGD,
        "step",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("optimizer.step is forbidden in Phase 5 mock")
        ),
    )
    model, optimizer = _structural_model_optimizer()
    checkpoint = tmp_path / "epoch-001.pt"
    summary = AttemptSummary(782, 782, 0, 782, 782)
    manifest = save_formal_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=tmp_path,
        model=model,
        optimizer=optimizer,
        completed_epoch=1,
        master_seed=1021082110,
        attempt_summary=summary,
        provenance=_provenance(),
        cuda_device_indices=(),
    )
    target_model, target_optimizer = _structural_model_optimizer()
    result = load_formal_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=tmp_path,
        model=target_model,
        optimizer=target_optimizer,
        expected_master_seed=1021082110,
        expected_provenance=_provenance(),
        expected_cuda_device_indices=(),
    )
    assert result.accepted_trajectory_steps == 782
    assert result.physical_call_lower_bound == result.physical_call_upper_bound == 782
    assert result.checkpoint_sha256 == manifest["sha256"]
    assert manifest["master_seed"] == 1021082110


def test_mock_accounting_orders_intent_call_completion_and_preserves_failure(
    tmp_path: Path,
) -> None:
    launch = _launch()
    authorization = _verified_authorization(tmp_path)
    ledger = AppendOnlyAttemptLedger(tmp_path / "ledger.jsonl", create=True)
    observed: list[str] = []
    execute_accounted_optimizer_call(
        coordinates=FormalStepCoordinates(1021082110, 1, 0, 1),
        ledger=ledger,
        optimizer_call=lambda: observed.append("mock-call"),
        authorization=authorization,
        expected_launch=launch,
        observed_launch=launch,
    )
    assert observed == ["mock-call"]
    assert [record["event"] for record in ledger.records] == ["intent", "completion"]

    failed = AppendOnlyAttemptLedger(tmp_path / "failed.jsonl", create=True)
    with pytest.raises(RuntimeError, match="mock crash"):
        execute_accounted_optimizer_call(
            coordinates=FormalStepCoordinates(1021082110, 1, 0, 1),
            ledger=failed,
            optimizer_call=lambda: (_ for _ in ()).throw(RuntimeError("mock crash")),
            authorization=authorization,
            expected_launch=launch,
            observed_launch=launch,
        )
    assert failed.summary().unresolved_intents == 1


def test_formal_run_root_is_full_hash_scoped_create_new_and_ordered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = require_create_new_formal_run_root(tmp_path, "A" * 64, 1021082110)
    assert target == tmp_path / ("A" * 64) / "seed-1021082110"
    with pytest.raises(FileExistsError):
        require_create_new_formal_run_root(tmp_path, "A" * 64, 1021082110)
    with pytest.raises(RuntimeError, match="Earlier formal seed"):
        require_create_new_formal_run_root(tmp_path, "B" * 64, 1747066946)

    observed: list[int] = []
    monkeypatch.setattr(
        "densenet_reproduction.formal_runtime._require_completed_formal_seed",
        lambda root, digest, seed: observed.append(seed),
    )
    ordered = require_create_new_formal_run_root(
        tmp_path, "C" * 64, 1747066946
    )
    assert ordered.name == "seed-1747066946"
    assert observed == [1021082110]
    assert require_formal_seed_training_order(
        tmp_path, "C" * 64, 1747066946, resuming=True
    ) == ordered


def test_phase5_tests_contain_no_optimizer_step_call() -> None:
    for path in (
        PROJECT_ROOT / "tests" / "test_corrective_freeze_guards.py",
        PROJECT_ROOT / "tests" / "test_phase5_freeze_primitives.py",
        PROJECT_ROOT / "tests" / "test_phase5_formal_checkpoint.py",
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != "step"
