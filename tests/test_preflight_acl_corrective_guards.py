from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import densenet_reproduction.data as data_module
import densenet_reproduction.formal_cli as formal_cli
import densenet_reproduction.formal_evaluation as formal_evaluation
from densenet_reproduction.data import (
    Cifar10BinaryDataset,
    verify_prepared_cifar10_split,
)
from densenet_reproduction.formal_evaluation import (
    FormalEvaluationRequest,
    run_formal_final_evaluation,
)
from densenet_reproduction.phase5 import LaunchIdentity, Phase6Authorization


FROZEN_ACCOUNT = "REDACTED_DOMAIN\\REDACTED_ACCOUNT"
FROZEN_SID = "<REDACTED_EXECUTION_SID>"


def _launch() -> LaunchIdentity:
    return LaunchIdentity(
        freeze_manifest_sha256="A" * 64,
        source_commit="b" * 40,
        config_sha256="C" * 64,
        dataset_sha256="D" * 64,
        project_wheel_sha256="E" * 64,
        python_runtime_sha256="F" * 64,
        environment_manifest_sha256="1" * 64,
        execution_account=FROZEN_ACCOUNT,
        execution_sid=FROZEN_SID,
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


def _authorization() -> Phase6Authorization:
    return Phase6Authorization("A" * 64, "2" * 64, "3" * 64)


def _prepared(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    include_test: bool = False,
) -> Path:
    monkeypatch.setattr(data_module, "CIFAR10_BINARY_BATCH_BYTES", 4)
    prepared = tmp_path / "prepared"
    prepared.mkdir()
    files: dict[str, dict[str, object]] = {}
    for index in range(1, 6):
        name = f"data_batch_{index}.bin"
        payload = bytes([index]) * 4
        (prepared / name).write_bytes(payload)
        files[name] = {
            "bytes": 4,
            "sha256": hashlib.sha256(payload).hexdigest().upper(),
        }
    test_payload = b"test"
    if include_test:
        (prepared / "test_batch.bin").write_bytes(test_payload)
    files["test_batch.bin"] = {
        "bytes": 4,
        "sha256": hashlib.sha256(test_payload).hexdigest().upper(),
    }
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


def _arguments(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        authorization=tmp_path / "authorization.json",
        command="train",
        config=tmp_path / "config.json",
        dataset_archive=tmp_path / "dataset.tar.gz",
        device_index=0,
        formal_root=tmp_path / "formal",
        freeze_manifest=tmp_path / "freeze.json",
        installed_environment_manifest=tmp_path / "environment.json",
        phase5_completion_decision=tmp_path / "d024.json",
        phase6_entry_decision=tmp_path / "d025.json",
        prepared_directory=tmp_path / "prepared",
        project_wheel=tmp_path / "project.whl",
        python_runtime_archive=tmp_path / "python.zip",
        python_runtime_manifest=tmp_path / "runtime.json",
        resume_checkpoint=None,
        resume_initial_boundary=False,
        seed=1021082110,
    )


def _mock_common_preflight(
    monkeypatch: pytest.MonkeyPatch, *, observed: LaunchIdentity | None = None
) -> None:
    launch = observed or _launch()
    monkeypatch.setattr(formal_cli, "_authorization", lambda path: _authorization())
    monkeypatch.setattr(formal_cli, "enforce_formal_runtime_policy", lambda index: None)
    monkeypatch.setattr(
        formal_cli,
        "observe_and_validate_launch",
        lambda **kwargs: ({"storage": {"required_bytes": 1}}, launch),
    )
    monkeypatch.setattr(formal_cli, "verify_phase6_decision_artifacts", lambda *a, **k: None)


def test_train_verifier_and_dataset_never_require_test_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepared(tmp_path, monkeypatch, include_test=False)
    verification = verify_prepared_cifar10_split(
        prepared, split="train", expected_archive_sha256="D" * 64
    )
    assert [name for name, _, _ in verification.files] == [
        f"data_batch_{index}.bin" for index in range(1, 6)
    ]
    dataset = Cifar10BinaryDataset(prepared, split="train")
    try:
        assert all(path.name != "test_batch.bin" for path in dataset._paths)
    finally:
        dataset.close()
    with pytest.raises(FileNotFoundError):
        verify_prepared_cifar10_split(
            prepared, split="test", expected_archive_sha256="D" * 64
        )


def test_training_member_missing_or_wrong_hash_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepared(tmp_path, monkeypatch)
    (prepared / "data_batch_3.bin").unlink()
    with pytest.raises(FileNotFoundError):
        verify_prepared_cifar10_split(prepared, split="train")
    (prepared / "data_batch_3.bin").write_bytes(b"3333")
    manifest_path = prepared / "prepared-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["data_batch_3.bin"]["sha256"] = "F" * 64
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        verify_prepared_cifar10_split(prepared, split="train")


def test_training_member_symlink_guard_precedes_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepared(tmp_path, monkeypatch)
    original = Path.is_symlink

    def observed_symlink(path: Path) -> bool:
        if path.name == "data_batch_2.bin":
            return True
        return original(path)

    monkeypatch.setattr(Path, "is_symlink", observed_symlink)
    with pytest.raises(ValueError, match="may not be a symlink"):
        verify_prepared_cifar10_split(prepared, split="train")


def test_preflight_prepared_failure_precedes_formal_root_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arguments = _arguments(tmp_path)
    _mock_common_preflight(monkeypatch)
    monkeypatch.setattr(
        formal_cli,
        "verify_prepared_cifar10_split",
        lambda *a, **k: (_ for _ in ()).throw(PermissionError("prepared denied")),
    )
    monkeypatch.setattr(
        formal_cli.shutil,
        "disk_usage",
        lambda path: (_ for _ in ()).throw(AssertionError("formal root reached")),
    )
    with pytest.raises(PermissionError, match="prepared denied"):
        formal_cli._preflight(arguments)


def test_wrong_execution_identity_fails_before_prepared_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arguments = _arguments(tmp_path)
    monkeypatch.setattr(formal_cli, "_authorization", lambda path: _authorization())
    monkeypatch.setattr(formal_cli, "enforce_formal_runtime_policy", lambda index: None)
    monkeypatch.setattr(
        formal_cli,
        "observe_and_validate_launch",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("Formal launch execution account/SID mismatch")
        ),
    )
    monkeypatch.setattr(
        formal_cli,
        "verify_prepared_cifar10_split",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("prepared accessed")),
    )
    with pytest.raises(RuntimeError, match="account/SID mismatch"):
        formal_cli._preflight(arguments)


def test_main_prepared_failure_precedes_seed_directory_and_training_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arguments = _arguments(tmp_path)
    _mock_common_preflight(monkeypatch)
    monkeypatch.setattr(formal_cli, "validate_formal_config", lambda path: {})
    monkeypatch.setattr(
        formal_cli,
        "verify_prepared_cifar10_split",
        lambda *a, **k: (_ for _ in ()).throw(PermissionError("prepared denied")),
    )
    monkeypatch.setattr(
        formal_cli,
        "require_create_new_formal_run_root",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("seed directory created")),
    )
    monkeypatch.setattr(
        formal_cli,
        "run_formal_training_seed",
        lambda request: (_ for _ in ()).throw(AssertionError("training adapter reached")),
    )
    argv = [
        "densenet-formal-runner",
        "train",
        "--config", str(arguments.config),
        "--freeze-manifest", str(arguments.freeze_manifest),
        "--authorization", str(arguments.authorization),
        "--phase5-completion-decision", str(arguments.phase5_completion_decision),
        "--phase6-entry-decision", str(arguments.phase6_entry_decision),
        "--dataset-archive", str(arguments.dataset_archive),
        "--project-wheel", str(arguments.project_wheel),
        "--python-runtime-archive", str(arguments.python_runtime_archive),
        "--python-runtime-manifest", str(arguments.python_runtime_manifest),
        "--installed-environment-manifest", str(arguments.installed_environment_manifest),
        "--prepared-directory", str(arguments.prepared_directory),
        "--formal-root", str(arguments.formal_root),
        "--seed", str(arguments.seed),
    ]
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(PermissionError, match="prepared denied"):
        formal_cli.main()


def _evaluation_request(tmp_path: Path) -> FormalEvaluationRequest:
    launch = _launch()
    return FormalEvaluationRequest(
        prepared_directory=tmp_path / "prepared",
        formal_root=tmp_path / "formal",
        master_seed=1021082110,
        device_index=0,
        authorization=_authorization(),
        expected_launch=launch,
        observed_launch=launch,
    )


def test_evaluation_gate_precedes_test_prepared_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "formal").mkdir()
    monkeypatch.setattr(formal_evaluation, "require_phase6_authorization", lambda *a, **k: None)
    monkeypatch.setattr(
        formal_evaluation,
        "_verify_all_training_complete",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("training incomplete")),
    )
    monkeypatch.setattr(
        formal_evaluation,
        "verify_prepared_cifar10_split",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("test bytes accessed")),
    )
    with pytest.raises(RuntimeError, match="training incomplete"):
        run_formal_final_evaluation(_evaluation_request(tmp_path))


def test_test_verification_occurs_after_gate_but_before_attempt_or_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "formal"
    freeze_root = root / ("A" * 64)
    for seed in (1021082110, 1747066946, 869460408):
        (freeze_root / f"seed-{seed}").mkdir(parents=True)
    monkeypatch.setattr(formal_evaluation, "require_phase6_authorization", lambda *a, **k: None)
    monkeypatch.setattr(formal_evaluation, "_verify_all_training_complete", lambda *a, **k: {})

    class ReachedTestVerification(RuntimeError):
        pass

    monkeypatch.setattr(
        formal_evaluation,
        "verify_prepared_cifar10_split",
        lambda *a, **k: (_ for _ in ()).throw(ReachedTestVerification("test verify")),
    )
    monkeypatch.setattr(
        formal_evaluation,
        "build_project_seeded_model",
        lambda seed: (_ for _ in ()).throw(AssertionError("model constructed")),
    )
    with pytest.raises(ReachedTestVerification, match="test verify"):
        run_formal_final_evaluation(_evaluation_request(tmp_path))
    seed_root = freeze_root / "seed-1021082110"
    assert not (seed_root / "final-test-attempt.json").exists()
    assert not (seed_root / "final-test-progress.jsonl").exists()


def test_acl_corrective_script_is_minimal_and_forbids_takeover() -> None:
    script = (
        Path(__file__).resolve().parents[1] / "scripts" / "phase6_acl_corrective.ps1"
    ).read_text(encoding="utf-8")
    required = (
        "$ApprovedSid = $ExecutionSid",
        "[Parameter(Mandatory = $true)]",
        "(OI)(CI)(RX)",
        "Get-FileHash -Algorithm SHA256",
        "ReadAndExecute",
        "Synchronize",
        "Set-Acl -LiteralPath $target.FullName",
        "did not receive exactly one read/traverse ACE",
        "ACL correction must run as the existing directory owner",
        "data_bytes_sha256_unchanged = $true",
    )
    assert all(token in script for token in required)
    forbidden = (
        "takeown",
        "/reset",
        "/setowner",
        "/inheritance:r",
        "/grant:r",
        "icacls.exe",
        "(M)",
        "(F)",
    )
    lowered = script.casefold()
    assert all(token.casefold() not in lowered for token in forbidden)
