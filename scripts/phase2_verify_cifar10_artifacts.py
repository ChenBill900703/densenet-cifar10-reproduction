"""Verify two Toronto CIFAR-10 archives and compare every image/label record.

The Python pickle archive is opened only after its MD5 and SHA256 match the
committed lock.  This script creates no model or optimizer and computes no
accuracy.  It emits Phase 2 artifact evidence, not a Phase 5 dataset freeze.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import tarfile
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = PROJECT_ROOT / "evidence" / "cifar10-artifacts.json"
DEFAULT_PYTHON_ARCHIVE = PROJECT_ROOT / "data" / "raw" / "cifar-10-python.tar.gz"
DEFAULT_BINARY_ARCHIVE = PROJECT_ROOT / "data" / "raw" / "cifar-10-binary.tar.gz"
CLASS_NAMES = (
    "airplane",
    "automobile",
    "bird",
    "cat",
    "deer",
    "dog",
    "frog",
    "horse",
    "ship",
    "truck",
)
TRAIN_NAMES = tuple(f"data_batch_{index}" for index in range(1, 6))
TEST_NAMES = ("test_batch",)
ALL_NAMES = TRAIN_NAMES + TEST_NAMES
RECORD_BYTES = 3_073
RECORDS_PER_BATCH = 10_000


def _git_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    return {"commit": commit, "worktree_clean_before_output": status == ""}


def _file_hashes(path: Path) -> dict[str, str | int]:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(chunk)
            sha256.update(chunk)
    return {
        "bytes": path.stat().st_size,
        "md5": md5.hexdigest().upper(),
        "sha256": sha256.hexdigest().upper(),
    }


def _verify_artifact(path: Path, record: dict[str, Any]) -> dict[str, str | int]:
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"artifact is not a regular file: {resolved}")
    actual = _file_hashes(resolved)
    for field in ("bytes", "md5", "sha256"):
        expected = record[field]
        if isinstance(expected, str):
            expected = expected.upper()
        if actual[field] != expected:
            raise ValueError(
                f"{field} mismatch for {resolved}: {actual[field]} != {expected}"
            )
    return {"path": str(resolved), **actual}


def _regular_member(archive: tarfile.TarFile, name: str) -> tarfile.TarInfo:
    matches = [member for member in archive.getmembers() if member.name == name]
    if len(matches) != 1:
        raise ValueError(f"expected one tar member {name!r}, found {len(matches)}")
    member = matches[0]
    if not member.isfile():
        raise ValueError(f"tar member is not a regular file: {name}")
    return member


def _validate_records(records: np.ndarray, name: str) -> np.ndarray:
    if records.shape != (RECORDS_PER_BATCH, RECORD_BYTES):
        raise ValueError(f"wrong canonical record shape for {name}: {records.shape}")
    if records.dtype != np.uint8:
        raise ValueError(f"wrong canonical record dtype for {name}: {records.dtype}")
    labels = records[:, 0]
    if int(labels.min()) < 0 or int(labels.max()) > 9:
        raise ValueError(f"label outside 0..9 in {name}")
    return np.ascontiguousarray(records)


def _binary_records(archive: tarfile.TarFile, batch_name: str) -> np.ndarray:
    member_name = f"cifar-10-batches-bin/{batch_name}.bin"
    member = _regular_member(archive, member_name)
    if member.size != RECORDS_PER_BATCH * RECORD_BYTES:
        raise ValueError(f"wrong byte size for {member_name}: {member.size}")
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError(f"could not open {member_name}")
    with stream:
        payload = stream.read()
    records = np.frombuffer(payload, dtype=np.uint8).reshape(
        RECORDS_PER_BATCH, RECORD_BYTES
    )
    return _validate_records(records, member_name)


def _python_records(archive: tarfile.TarFile, batch_name: str) -> np.ndarray:
    member_name = f"cifar-10-batches-py/{batch_name}"
    member = _regular_member(archive, member_name)
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError(f"could not open {member_name}")
    with stream:
        payload = pickle.load(stream, encoding="bytes")  # noqa: S301 - hash gated
    if not isinstance(payload, dict):
        raise ValueError(f"unexpected pickle object in {member_name}")
    data = payload.get(b"data")
    labels = payload.get(b"labels")
    if not isinstance(data, np.ndarray) or data.shape != (
        RECORDS_PER_BATCH,
        RECORD_BYTES - 1,
    ):
        raise ValueError(f"wrong data array in {member_name}")
    if data.dtype != np.uint8:
        raise ValueError(f"wrong data dtype in {member_name}: {data.dtype}")
    if not isinstance(labels, Sequence) or len(labels) != RECORDS_PER_BATCH:
        raise ValueError(f"wrong labels object in {member_name}")
    if any(
        isinstance(label, bool) or not isinstance(label, int) or not 0 <= label <= 9
        for label in labels
    ):
        raise ValueError(f"invalid Python labels in {member_name}")
    label_array = np.asarray(labels, dtype=np.uint8)
    records = np.empty((RECORDS_PER_BATCH, RECORD_BYTES), dtype=np.uint8)
    records[:, 0] = label_array
    records[:, 1:] = data
    return _validate_records(records, member_name)


def _python_class_names(archive: tarfile.TarFile) -> tuple[str, ...]:
    member = _regular_member(archive, "cifar-10-batches-py/batches.meta")
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError("could not open Python batches.meta")
    with stream:
        payload = pickle.load(stream, encoding="bytes")  # noqa: S301 - hash gated
    if not isinstance(payload, dict) or not isinstance(
        payload.get(b"label_names"), Sequence
    ):
        raise ValueError("invalid Python batches.meta")
    names = tuple(
        name.decode("ascii") if isinstance(name, bytes) else str(name)
        for name in payload[b"label_names"]
    )
    return names


def _binary_class_names(
    archive: tarfile.TarFile,
) -> tuple[tuple[str, ...], int]:
    member = _regular_member(archive, "cifar-10-batches-bin/batches.meta.txt")
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError("could not open binary batches.meta.txt")
    with stream:
        lines = stream.read().decode("ascii").splitlines()
    terminal_blank_lines = 0
    while lines and lines[-1] == "":
        lines.pop()
        terminal_blank_lines += 1
    return tuple(lines), terminal_blank_lines


def _batch_record(
    name: str, python_records: np.ndarray, binary_records: np.ndarray
) -> dict[str, Any]:
    python_digest = hashlib.sha256(python_records.tobytes()).hexdigest().upper()
    binary_digest = hashlib.sha256(binary_records.tobytes()).hexdigest().upper()
    if python_digest != binary_digest or not np.array_equal(
        python_records, binary_records
    ):
        raise ValueError(f"semantic record mismatch in {name}")
    histogram = np.bincount(binary_records[:, 0], minlength=10).tolist()
    return {
        "name": name,
        "records": RECORDS_PER_BATCH,
        "canonical_label_plus_chw_pixels_sha256": binary_digest,
        "class_histogram": histogram,
        "byte_exact_between_archives": True,
    }


def verify_archives(
    *,
    python_archive_path: Path,
    binary_archive_path: Path,
    lock_path: Path,
) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("classification") != "PHASE2-CIFAR10-APPROVED-ARTIFACT-LOCK":
        raise ValueError("unexpected CIFAR-10 artifact lock classification")
    artifacts = lock["artifacts"]
    python_identity = _verify_artifact(
        python_archive_path, artifacts["toronto_python"]
    )
    binary_identity = _verify_artifact(
        binary_archive_path, artifacts["toronto_binary"]
    )

    batch_records: list[dict[str, Any]] = []
    split_digests = {"train": hashlib.sha256(), "test": hashlib.sha256()}
    split_histograms = {
        "train": np.zeros(10, dtype=np.int64),
        "test": np.zeros(10, dtype=np.int64),
    }
    with tarfile.open(python_archive_path, "r:gz") as python_archive, tarfile.open(
        binary_archive_path, "r:gz"
    ) as binary_archive:
        python_class_names = _python_class_names(python_archive)
        binary_class_names, binary_terminal_blank_lines = _binary_class_names(
            binary_archive
        )
        if python_class_names != CLASS_NAMES or binary_class_names != CLASS_NAMES:
            raise ValueError(
                "class-name metadata differs from the official 10-class order"
            )
        for name in ALL_NAMES:
            python_records = _python_records(python_archive, name)
            binary_records = _binary_records(binary_archive, name)
            batch_records.append(_batch_record(name, python_records, binary_records))
            split = "train" if name in TRAIN_NAMES else "test"
            split_digests[split].update(binary_records.tobytes())
            split_histograms[split] += np.bincount(
                binary_records[:, 0], minlength=10
            )

    expected_histograms = {"train": [5_000] * 10, "test": [1_000] * 10}
    observed_histograms = {
        split: values.tolist() for split, values in split_histograms.items()
    }
    if observed_histograms != expected_histograms:
        raise ValueError(f"unexpected class histograms: {observed_histograms}")

    return {
        "classification": "PHASE2-CIFAR10-ARTIFACT-DIAGNOSTIC-NOT-FORMAL-FREEZE",
        "evidence_class": "DERIVED",
        "record_date": date.today().isoformat(),
        "project_git": _git_state(),
        "optimizer_constructed": False,
        "optimizer_steps": 0,
        "accuracy_computed": False,
        "artifacts": {
            "toronto_python": python_identity,
            "toronto_binary": binary_identity,
        },
        "batches": batch_records,
        "splits": {
            "train": {
                "records": 50_000,
                "class_histogram": observed_histograms["train"],
                "canonical_label_plus_chw_pixels_sha256": split_digests[
                    "train"
                ].hexdigest().upper(),
            },
            "test": {
                "records": 10_000,
                "class_histogram": observed_histograms["test"],
                "canonical_label_plus_chw_pixels_sha256": split_digests[
                    "test"
                ].hexdigest().upper(),
            },
        },
        "semantic_equivalence": {
            "all_60000_labels_and_images_byte_exact": True,
            "class_names_semantically_equal": True,
            "class_names": CLASS_NAMES,
            "metadata_byte_exact": False,
            "binary_metadata_terminal_blank_lines": binary_terminal_blank_lines,
            "metadata_difference": "binary batches.meta.txt contains a terminal blank line absent from Python label_names",
            "canonical_record_layout": "uint8 label 0..9 followed by 3072 CHW row-major uint8 pixels",
        },
        "historical_torch7_archive": lock["artifacts"]["historical_torch7"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--python-archive", type=Path, default=DEFAULT_PYTHON_ARCHIVE)
    parser.add_argument("--binary-archive", type=Path, default=DEFAULT_BINARY_ARCHIVE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify_archives(
        python_archive_path=args.python_archive,
        binary_archive_path=args.binary_archive,
        lock_path=args.lock,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
