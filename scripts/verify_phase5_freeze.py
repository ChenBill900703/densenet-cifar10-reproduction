"""Read-only verification of a complete Phase 5 freeze candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

from densenet_reproduction.phase5 import (
    ArtifactIdentity,
    read_canonical_json,
    sha256_bytes,
    sha256_file,
    validate_freeze_manifest,
)


def _resolve_identity(root: Path, identity: dict[str, object]) -> Path:
    record = ArtifactIdentity(**identity)
    candidate = (root / PurePosixPath(record.path)).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("Freeze artifact escapes the project root.") from error
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError("Freeze artifact is not a regular non-symlink file.")
    if candidate.stat().st_size != record.bytes or sha256_file(candidate) != record.sha256:
        raise ValueError(f"Freeze artifact identity mismatch: {record.path}")
    return candidate


def _verify_runtime_archive(archive_path: Path, manifest_path: Path) -> int:
    manifest = read_canonical_json(manifest_path)
    expected = {record["path"]: record for record in manifest["files"]}
    observed: set[str] = set()
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            name = info.filename
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or name in observed:
                raise ValueError("Python runtime archive contains an unsafe/duplicate path.")
            observed.add(name)
            if name not in expected or info.is_dir():
                raise ValueError("Python runtime archive contains an unexpected entry.")
            payload = archive.read(info)
            record = expected[name]
            if len(payload) != record["bytes"] or sha256_bytes(payload) != record["sha256"]:
                raise ValueError(f"Python runtime archive entry mismatch: {name}")
    if observed != set(expected):
        raise ValueError("Python runtime archive is missing locked entries.")
    if manifest["archive"]["sha256"] != sha256_file(archive_path):
        raise ValueError("Python runtime archive/manifest hash mismatch.")
    return len(observed)


def _verify_wheelhouse(wheelhouse: Path, manifest_path: Path) -> int:
    manifest = read_canonical_json(manifest_path)
    records = manifest["artifacts"]
    expected_names = {record["filename"] for record in records}
    observed_names = {
        path.name for path in wheelhouse.iterdir() if path.is_file() and not path.is_symlink()
    }
    if observed_names != expected_names:
        raise ValueError("Wheelhouse filenames differ from the locked manifest.")
    for record in records:
        path = wheelhouse / record["filename"]
        if path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
            raise ValueError(f"Wheelhouse artifact mismatch: {path.name}")
    return len(records)


def _verify_project_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        required = {
            "densenet_reproduction/formal_cli.py",
            "densenet_reproduction/formal_training.py",
            "densenet_reproduction/formal_evaluation.py",
            "densenet_reproduction/formal_checkpoint.py",
            "densenet_reproduction/phase5_launch.py",
            "densenet_reproduction-0.1.0.dist-info/entry_points.txt",
        }
        if not required.issubset(names):
            raise ValueError("Project wheel omits frozen formal runtime modules/entry point.")
        entry_points = archive.read(
            "densenet_reproduction-0.1.0.dist-info/entry_points.txt"
        ).decode("utf-8")
        if "densenet-formal-runner = densenet_reproduction.formal_cli:main_entry" not in entry_points:
            raise ValueError("Project wheel formal CLI entry point mismatch.")


def verify(
    root: Path, manifest_path: Path, wheelhouse: Path, source_bundle: Path
) -> dict[str, object]:
    project_root = root.resolve(strict=True)
    document = read_canonical_json(manifest_path)
    validate_freeze_manifest(document)
    paths: dict[str, Path] = {}
    paths["config"] = _resolve_identity(project_root, document["config"])
    paths["dataset"] = _resolve_identity(project_root, document["dataset"])
    for name, identity in document["artifacts"].items():
        paths[name] = _resolve_identity(project_root, identity)
    bundle = source_bundle.resolve(strict=True)
    if bundle.is_symlink() or not bundle.is_file():
        raise ValueError("Freeze-source bundle is missing or unsafe.")
    if (
        bundle.stat().st_size != document["source"]["git_bundle_bytes"]
        or sha256_file(bundle) != document["source"]["git_bundle_sha256"]
    ):
        raise ValueError("Freeze-source bundle identity mismatch.")
    subprocess.run(
        ["git", "bundle", "verify", str(bundle)],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    _verify_project_wheel(paths["project_wheel"])
    wheel_count = _verify_wheelhouse(wheelhouse.resolve(strict=True), paths["wheelhouse_manifest"])
    runtime_count = _verify_runtime_archive(
        paths["python_runtime_archive"], paths["python_runtime_manifest"]
    )
    return {
        "classification": "PHASE5-FREEZE-CANDIDATE-VERIFICATION",
        "evidence_class": "DERIVED",
        "formal_optimizer_steps": 0,
        "freeze_manifest_sha256": sha256_file(manifest_path),
        "ok": True,
        "runtime_files_verified": runtime_count,
        "wheel_artifacts_verified": wheel_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--source-bundle", type=Path, required=True)
    arguments = parser.parse_args()
    print(
        json.dumps(
            verify(
                arguments.root,
                arguments.manifest,
                arguments.wheelhouse,
                arguments.source_bundle,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, TypeError, ValueError, zipfile.BadZipFile) as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        raise SystemExit(2) from error
