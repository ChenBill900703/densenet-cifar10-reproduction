"""Verify committed and external evidence sources against the source lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = PROJECT_ROOT / "evidence" / "source-lock.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _git_optional(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode not in (0, 1):
        raise subprocess.CalledProcessError(completed.returncode, completed.args)
    return completed.stdout.strip()


def _is_detached(repo: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo), "symbolic-ref", "-q", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode not in (0, 1):
        raise subprocess.CalledProcessError(completed.returncode, completed.args)
    return completed.returncode == 1


def _resolve(
    project_root: Path, configured_path: str, path_environment: str | None = None
) -> Path:
    override = os.environ.get(path_environment) if path_environment else None
    path = Path(override or configured_path)
    return path if path.is_absolute() else project_root / path


def verify_source_lock(lock_path: Path, project_root: Path) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    repository_results = []
    file_results = []

    for entry in lock["repositories"]:
        repo = _resolve(project_root, entry["path"])
        result: dict[str, Any] = {"path": entry["path"], "ok": False}
        try:
            if not repo.is_dir():
                raise FileNotFoundError(repo)
            head = _git(repo, "rev-parse", "HEAD")
            remote = _git(repo, "remote", "get-url", "origin")
            dirty = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
            detached = _is_detached(repo)
            remote_head = _git(repo, "rev-parse", "refs/remotes/origin/HEAD")
            shallow_text = _git(repo, "rev-parse", "--is-shallow-repository")
            if shallow_text not in ("true", "false"):
                raise ValueError(
                    f"Unexpected --is-shallow-repository value: {shallow_text}"
                )
            partial_clone_config = _git_optional(
                repo,
                "config",
                "--local",
                "--get-regexp",
                r"^(extensions\.partialclone|remote\..*\.(promisor|partialclonefilter))$",
            )
            partial_clone = bool(partial_clone_config)
            object_listing = _git(repo, "rev-list", "--objects", "--all", "--missing=print")
            missing_objects = sum(
                line.startswith("?") for line in object_listing.splitlines()
            )
            required_commits = entry["required_commits"]
            for required_commit in required_commits:
                _git(repo, "cat-file", "-e", f"{required_commit}^{{commit}}")
            required_commits_present = True
            ancestor_check = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "merge-base",
                    "--is-ancestor",
                    entry["commit"],
                    remote_head,
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if ancestor_check.returncode not in (0, 1):
                raise subprocess.CalledProcessError(
                    ancestor_check.returncode, ancestor_check.args
                )
            pin_is_ancestor = ancestor_check.returncode == 0
            required_history_complete = (
                shallow_text == "false" and not partial_clone and missing_objects == 0
                and required_commits_present
                and remote_head == entry["remote_head"]
                and pin_is_ancestor
            )
            _git(repo, "fsck", "--no-dangling")
            result.update(
                {
                    "head": head,
                    "remote": remote,
                    "clean": not dirty,
                    "detached": detached,
                    "required_history_complete": required_history_complete,
                    "remote_head": remote_head,
                    "required_commits_present": required_commits_present,
                    "pin_is_ancestor_of_remote_head": pin_is_ancestor,
                    "shallow": shallow_text == "true",
                    "partial_clone": partial_clone,
                    "missing_objects": missing_objects,
                    "object_integrity": True,
                }
            )
            if head != entry["commit"]:
                errors.append(f"{entry['path']}: commit {head} != {entry['commit']}")
            if remote != entry["remote"]:
                errors.append(f"{entry['path']}: remote {remote} != {entry['remote']}")
            if remote_head != entry["remote_head"]:
                errors.append(
                    f"{entry['path']}: remote HEAD {remote_head} != "
                    f"{entry['remote_head']}"
                )
            if dirty:
                errors.append(f"{entry['path']}: working tree is dirty")
            if not detached:
                errors.append(f"{entry['path']}: HEAD is not detached")
            if shallow_text == "true":
                errors.append(f"{entry['path']}: repository is a shallow clone")
            if partial_clone:
                errors.append(f"{entry['path']}: repository is a partial/promisor clone")
            if missing_objects:
                errors.append(
                    f"{entry['path']}: repository has {missing_objects} missing objects"
                )
            if not pin_is_ancestor:
                errors.append(
                    f"{entry['path']}: pin is not an ancestor of locked remote HEAD"
                )
            result["ok"] = (
                head == entry["commit"]
                and remote == entry["remote"]
                and not dirty
                and detached
                and required_history_complete
            )
        except (
            FileNotFoundError,
            KeyError,
            ValueError,
            subprocess.CalledProcessError,
        ) as error:
            errors.append(f"{entry['path']}: {type(error).__name__}: {error}")
        repository_results.append(result)

    for entry in lock["files"]:
        path_environment = entry.get("path_env")
        path = _resolve(project_root, entry["path"], path_environment)
        result = {
            "path": entry["path"],
            "resolved_path": str(path),
            "path_source": (
                f"environment:{path_environment}"
                if path_environment and os.environ.get(path_environment)
                else "lock-default"
            ),
            "ok": False,
        }
        try:
            observed = _sha256(path)
            result["sha256"] = observed
            result["ok"] = observed == entry["sha256"]
            if not result["ok"]:
                errors.append(f"{entry['path']}: SHA256 {observed} != {entry['sha256']}")
        except FileNotFoundError as error:
            errors.append(f"{entry['path']}: FileNotFoundError: {error}")
        file_results.append(result)

    return {
        "classification": lock["classification"],
        "evidence_class": lock["evidence_class"],
        "lock": str(lock_path),
        "repositories": repository_results,
        "files": file_results,
        "repositories_verified": sum(item["ok"] for item in repository_results),
        "files_verified": sum(item["ok"] for item in file_results),
        "errors": errors,
        "ok": not errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    arguments = parser.parse_args()
    report = verify_source_lock(arguments.lock.resolve(), PROJECT_ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
