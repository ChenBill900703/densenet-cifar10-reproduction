"""Self-observed, fail-closed formal launch identity checks."""

from __future__ import annotations

import csv
import ctypes
import platform
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

import torch

from .phase5 import (
    LaunchIdentity,
    canonical_json_bytes,
    read_canonical_json,
    sha256_bytes,
    sha256_file,
    validate_freeze_manifest,
    validate_launch_identity,
)
from .phase5_environment import (
    verify_installed_environment_manifest,
    verify_python_runtime_manifest,
)


def _windows_execution_identity() -> tuple[str, str]:
    """Observe the exact SAM-compatible account and token-user SID."""

    if sys.platform != "win32":
        raise RuntimeError("Formal execution identity requires Windows.")
    secur32 = ctypes.WinDLL("secur32", use_last_error=True)
    size = ctypes.c_ulong(0)
    secur32.GetUserNameExW(2, None, ctypes.byref(size))
    if size.value <= 1:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_unicode_buffer(size.value)
    if not secur32.GetUserNameExW(2, buffer, ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    account = buffer.value
    result = subprocess.run(
        ["whoami", "/user", "/fo", "csv", "/nh"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    rows = list(csv.reader(result.stdout.splitlines()))
    if len(rows) != 1 or len(rows[0]) != 2:
        raise RuntimeError("whoami did not return one account/SID record.")
    whoami_account, sid = (field.strip() for field in rows[0])
    if whoami_account.casefold() != account.casefold():
        raise RuntimeError("Windows account observations disagree.")
    return account, sid


def _nvidia_identity(device_index: int) -> tuple[str, str, str]:
    command = [
        "nvidia-smi",
        f"--id={device_index}",
        "--query-gpu=driver_version,name,uuid",
        "--format=csv,noheader,nounits",
    ]
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError("nvidia-smi did not identify exactly one frozen GPU.")
    fields = [field.strip() for field in lines[0].split(",")]
    if len(fields) != 3 or any(not field for field in fields):
        raise RuntimeError("nvidia-smi identity output is malformed.")
    return fields[0], fields[1], fields[2]


def load_freeze_manifest(path: Path) -> tuple[dict[str, Any], str]:
    document = read_canonical_json(path)
    if not isinstance(document, dict):
        raise ValueError("Freeze manifest must be an object.")
    validate_freeze_manifest(document)
    return document, sha256_bytes(canonical_json_bytes(document))


def expected_launch_identity(
    manifest: Mapping[str, Any], manifest_sha256: str
) -> LaunchIdentity:
    if manifest.get("schema_version") != 2:
        raise RuntimeError("Legacy freeze manifest is not eligible for corrected execution.")
    environment = manifest["environment"]
    return LaunchIdentity(
        freeze_manifest_sha256=manifest_sha256,
        source_commit=manifest["source"]["freeze_source_commit"],
        config_sha256=manifest["config"]["sha256"],
        dataset_sha256=manifest["dataset"]["sha256"],
        project_wheel_sha256=manifest["artifacts"]["project_wheel"]["sha256"],
        python_runtime_sha256=manifest["artifacts"]["python_runtime_archive"]["sha256"],
        environment_manifest_sha256=environment["installed_manifest_sha256"],
        execution_account=environment["execution_account"],
        execution_sid=environment["execution_sid"],
        windows_build=environment["windows_build"],
        python_build=environment["python_build"],
        driver_version=environment["driver_version"],
        gpu_name=environment["gpu_name"],
        gpu_uuid=environment["gpu_uuid"],
        compute_capability=environment["compute_capability"],
        deterministic_algorithms=True,
        cudnn_benchmark=False,
        cudnn_deterministic=True,
        convolution_precision="ieee",
        matmul_precision="ieee",
        amp_enabled=False,
        compile_enabled=False,
    )


def observe_and_validate_launch(
    *,
    freeze_manifest_path: Path,
    config_path: Path,
    dataset_archive_path: Path,
    project_wheel_path: Path,
    python_runtime_archive_path: Path,
    python_runtime_manifest_path: Path,
    installed_environment_manifest_path: Path,
    device_index: int,
) -> tuple[dict[str, Any], LaunchIdentity]:
    """Verify artifacts and the live host before model/dataset construction."""

    manifest, freeze_hash = load_freeze_manifest(freeze_manifest_path)
    expected = expected_launch_identity(manifest, freeze_hash)
    execution_account, execution_sid = _windows_execution_identity()
    if (
        execution_account != expected.execution_account
        or execution_sid != expected.execution_sid
    ):
        raise RuntimeError("Formal launch execution account/SID mismatch.")
    checks = (
        (config_path, manifest["config"]),
        (dataset_archive_path, manifest["dataset"]),
        (project_wheel_path, manifest["artifacts"]["project_wheel"]),
        (
            python_runtime_archive_path,
            manifest["artifacts"]["python_runtime_archive"],
        ),
        (
            python_runtime_manifest_path,
            manifest["artifacts"]["python_runtime_manifest"],
        ),
    )
    for path, identity in checks:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Launch artifact is missing or unsafe: {path}")
        if path.stat().st_size != identity["bytes"] or sha256_file(path) != identity["sha256"]:
            raise RuntimeError(f"Launch artifact identity mismatch: {path}")
    if sha256_file(installed_environment_manifest_path) != expected.environment_manifest_sha256:
        raise RuntimeError("Installed-environment manifest SHA256 mismatch.")
    verify_installed_environment_manifest(installed_environment_manifest_path)
    verify_python_runtime_manifest(Path(sys.base_prefix), python_runtime_manifest_path)
    driver, gpu_name, gpu_uuid = _nvidia_identity(device_index)
    if not torch.cuda.is_available() or device_index >= torch.cuda.device_count():
        raise RuntimeError("Frozen CUDA device is unavailable.")
    capability = torch.cuda.get_device_capability(device_index)
    try:
        amp_enabled = bool(torch.is_autocast_enabled("cuda"))
    except TypeError:  # pragma: no cover - compatibility is fail-closed below
        amp_enabled = bool(torch.is_autocast_enabled())
    observed = LaunchIdentity(
        freeze_manifest_sha256=freeze_hash,
        source_commit=manifest["source"]["freeze_source_commit"],
        config_sha256=sha256_file(config_path),
        dataset_sha256=sha256_file(dataset_archive_path),
        project_wheel_sha256=sha256_file(project_wheel_path),
        python_runtime_sha256=sha256_file(python_runtime_archive_path),
        environment_manifest_sha256=sha256_file(installed_environment_manifest_path),
        execution_account=execution_account,
        execution_sid=execution_sid,
        windows_build=platform.version(),
        python_build=sys.version,
        driver_version=driver,
        gpu_name=gpu_name,
        gpu_uuid=gpu_uuid,
        compute_capability=f"{capability[0]}.{capability[1]}",
        deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
        cudnn_benchmark=torch.backends.cudnn.benchmark,
        cudnn_deterministic=torch.backends.cudnn.deterministic,
        convolution_precision=torch.backends.cudnn.conv.fp32_precision,
        matmul_precision=torch.backends.cuda.matmul.fp32_precision,
        amp_enabled=amp_enabled,
        compile_enabled=torch.compiler.is_compiling(),
    )
    validate_launch_identity(expected, observed)
    return manifest, observed
