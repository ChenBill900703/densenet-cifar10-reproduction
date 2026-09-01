"""Assemble deterministic Phase 5 artifact manifests without executing wheels."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

from densenet_reproduction.phase5 import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from densenet_reproduction.phase5_environment import installed_environment_snapshot


def _write_new(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_json_bytes(document))


def _locked_distributions(path: Path) -> dict[str, str]:
    locked: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        name, version = value.split("==", maxsplit=1)
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        if normalized in locked:
            raise ValueError("Duplicate distribution in environment lock.")
        locked[normalized] = version
    return locked


def _wheel_metadata(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as archive:
        names = [
            name
            for name in archive.namelist()
            if name.endswith(".dist-info/METADATA")
            and len(PurePosixPath(name).parts) == 2
        ]
        if len(names) != 1:
            raise ValueError(f"Wheel must contain exactly one METADATA: {path.name}")
        fields: dict[str, str] = {}
        for line in archive.read(names[0]).decode("utf-8").splitlines():
            if line.startswith("Name: "):
                fields["name"] = line[6:]
            elif line.startswith("Version: "):
                fields["version"] = line[9:]
        if set(fields) != {"name", "version"}:
            raise ValueError(f"Wheel metadata identity is incomplete: {path.name}")
        return fields["name"], fields["version"]


def wheelhouse_manifest(wheelhouse: Path, lock: Path) -> dict[str, object]:
    locked = _locked_distributions(lock)
    records: list[dict[str, object]] = []
    observed: dict[str, str] = {}
    for path in sorted(wheelhouse.glob("*.whl"), key=lambda value: value.name.casefold()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Wheelhouse entries must be regular non-symlink files.")
        name, version = _wheel_metadata(path)
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        if normalized in observed:
            raise ValueError("Wheelhouse has duplicate distribution identities.")
        observed[normalized] = version
        records.append(
            {
                "bytes": path.stat().st_size,
                "distribution": name,
                "filename": path.name,
                "index_origin": (
                    "https://download.pytorch.org/whl/cu130"
                    if normalized in {"torch", "torchvision"}
                    else "https://pypi.org/simple"
                ),
                "sha256": sha256_file(path),
                "version": version,
            }
        )
    if observed != locked:
        raise ValueError(
            f"Wheelhouse/lock mismatch: missing={sorted(set(locked)-set(observed))}, "
            f"extra={sorted(set(observed)-set(locked))}, "
            f"versions={[(name, locked.get(name), observed.get(name)) for name in sorted(set(locked)&set(observed)) if locked[name] != observed[name]]}"
        )
    return {
        "artifacts": records,
        "classification": "PHASE5-WHEELHOUSE-ARTIFACT-MANIFEST",
        "evidence_class": "DERIVED",
        "formal_optimizer_steps": 0,
        "network_required_for_reconstruction": False,
        "schema_version": 1,
    }


def _runtime_files(root: Path) -> list[Path]:
    resolved = root.resolve(strict=True)
    if not resolved.is_dir() or root.is_symlink():
        raise ValueError("Python runtime root must be a regular directory.")
    files: list[Path] = []
    casefolded: set[str] = set()
    for path in sorted(resolved.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Python runtime contains a symlink: {path}")
        relative_parts = path.relative_to(resolved).parts
        if "__pycache__" in relative_parts or path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if path.is_file():
            relative = path.relative_to(resolved).as_posix()
            if relative.casefold() in casefolded:
                raise ValueError("Python runtime contains case-colliding paths.")
            casefolded.add(relative.casefold())
            files.append(path)
    return files


def archive_python_runtime(root: Path, archive_path: Path) -> dict[str, object]:
    resolved = root.resolve(strict=True)
    files = _runtime_files(resolved)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    with archive_path.open("xb") as raw_stream:
        with zipfile.ZipFile(
            raw_stream,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            for path in files:
                relative = path.relative_to(resolved).as_posix()
                payload = path.read_bytes()
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 0
                info.external_attr = 0
                archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
                records.append(
                    {
                        "bytes": len(payload),
                        "path": relative,
                        "sha256": sha256_bytes(payload),
                    }
                )
    return {
        "archive": {
            "bytes": archive_path.stat().st_size,
            "filename": archive_path.name,
            "format": "deterministic-zip-deflate-level-9-fixed-1980-timestamps",
            "sha256": sha256_file(archive_path),
        },
        "classification": "PHASE5-PYTHON-RUNTIME-ARTIFACT-MANIFEST",
        "evidence_class": "DERIVED",
        "files": records,
        "formal_optimizer_steps": 0,
        "schema_version": 1,
        "source_root_recorded_separately": str(resolved),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    wheels = subparsers.add_parser("wheelhouse")
    wheels.add_argument("--wheelhouse", type=Path, required=True)
    wheels.add_argument("--lock", type=Path, required=True)
    wheels.add_argument("--output", type=Path, required=True)
    runtime = subparsers.add_parser("runtime")
    runtime.add_argument("--root", type=Path, required=True)
    runtime.add_argument("--archive", type=Path, required=True)
    runtime.add_argument("--output", type=Path, required=True)
    installed = subparsers.add_parser("installed")
    installed.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.command == "wheelhouse":
        report = wheelhouse_manifest(arguments.wheelhouse, arguments.lock)
    elif arguments.command == "runtime":
        report = archive_python_runtime(arguments.root, arguments.archive)
    else:
        report = installed_environment_snapshot()
    _write_new(arguments.output, report)
    print(sha256_file(arguments.output))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        raise SystemExit(2) from error
