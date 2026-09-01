"""Exact installed/runtime file inventories for Phase 5 and later launch checks."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path, PurePosixPath
import re
from typing import Any

from .phase5 import read_canonical_json, sha256_file


def installed_environment_snapshot() -> dict[str, object]:
    distributions: list[dict[str, object]] = []
    seen: set[str] = set()
    for distribution in sorted(
        metadata.distributions(), key=lambda item: (item.metadata["Name"] or "").lower()
    ):
        name = distribution.metadata["Name"]
        if not name:
            raise ValueError("Installed distribution has no Name metadata.")
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        if normalized in seen:
            raise ValueError(f"Duplicate installed distribution: {name}")
        seen.add(normalized)
        files: list[dict[str, object]] = []
        for file in sorted(distribution.files or (), key=lambda item: str(item).casefold()):
            located = Path(distribution.locate_file(file))
            if located.is_symlink() or not located.is_file():
                raise ValueError(f"Installed RECORD entry is unsafe or missing: {located}")
            files.append(
                {
                    "bytes": located.stat().st_size,
                    "path": str(PurePosixPath(file)),
                    "sha256": sha256_file(located),
                }
            )
        distributions.append(
            {
                "files": files,
                "name": name,
                "normalized_name": normalized,
                "version": distribution.version,
            }
        )
    return {
        "classification": "PHASE5-INSTALLED-ENVIRONMENT-FILE-MANIFEST",
        "distributions": distributions,
        "evidence_class": "DERIVED",
        "formal_optimizer_steps": 0,
        "schema_version": 1,
    }


def verify_installed_environment_manifest(path: Path) -> dict[str, Any]:
    expected = read_canonical_json(path)
    observed = installed_environment_snapshot()
    if expected != observed:
        raise RuntimeError("Live installed environment differs from the frozen manifest.")
    return expected


def verify_python_runtime_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    document = read_canonical_json(manifest_path)
    if not isinstance(document, dict) or set(document) != {
        "archive",
        "classification",
        "evidence_class",
        "files",
        "formal_optimizer_steps",
        "schema_version",
        "source_root_recorded_separately",
    }:
        raise ValueError("Unexpected Python-runtime manifest schema.")
    if (
        document["classification"] != "PHASE5-PYTHON-RUNTIME-ARTIFACT-MANIFEST"
        or document["evidence_class"] != "DERIVED"
        or document["formal_optimizer_steps"] != 0
        or document["schema_version"] != 1
    ):
        raise ValueError("Python-runtime manifest policy mismatch.")
    resolved = root.resolve(strict=True)
    observed: list[dict[str, object]] = []
    casefolded: set[str] = set()
    for path in sorted(resolved.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Live Python runtime contains a symlink: {path}")
        relative_parts = path.relative_to(resolved).parts
        if "__pycache__" in relative_parts or path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if path.is_file():
            relative = path.relative_to(resolved).as_posix()
            if relative.casefold() in casefolded:
                raise ValueError("Live Python runtime contains a case collision.")
            casefolded.add(relative.casefold())
            observed.append(
                {
                    "bytes": path.stat().st_size,
                    "path": relative,
                    "sha256": sha256_file(path),
                }
            )
    if observed != document["files"]:
        raise RuntimeError("Live Python runtime differs from the frozen file manifest.")
    return document
