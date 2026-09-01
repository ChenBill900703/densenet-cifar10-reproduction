"""Run a full data-only Phase 2 replay diagnostic on verified CIFAR-10 bytes.

No model, loss, optimizer, accuracy, or formal training step is constructed.
The report intentionally preserves the pre-approval H-003 candidate status of
the dated 2026-08-16 evidence record.  The later human approval is recorded by
D-010 without rewriting that historical machine output.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import torch
from torch.utils.data import DataLoader, SequentialSampler

from densenet_reproduction.data import (
    CIFAR10_TORONTO_BINARY_MD5,
    CIFAR10_CANDIDATE_STREAM_DOMAIN,
    AugmentedIndex,
    CandidateCifar10EpochSampler,
    Cifar10BinaryDataset,
    file_digest,
    prepare_cifar10_binary_archive,
    verify_file_identity,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = PROJECT_ROOT / "evidence" / "cifar10-artifacts.json"
DEFAULT_BINARY_ARCHIVE = PROJECT_ROOT / "data" / "raw" / "cifar-10-binary.tar.gz"
DEFAULT_PREPARED = PROJECT_ROOT / "data" / "prepared" / "cifar-10-batches-bin"
DIAGNOSTIC_MASTER_SEED = 1_021_082_110
DIAGNOSTIC_EPOCH = 1
DIAGNOSTIC_BATCH_SIZE = 64
DIAGNOSTIC_WORKER_GENERATOR_SEED = 20_260_816


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


def _new_digest() -> Any:
    return hashlib.sha256()


def _update_tensor_digest(digest: Any, tensor: torch.Tensor) -> None:
    contiguous = tensor.detach().cpu().contiguous()
    digest.update(str(contiguous.dtype).encode("ascii"))
    digest.update(str(tuple(contiguous.shape)).encode("ascii"))
    digest.update(contiguous.numpy().tobytes(order="C"))


def _loader_report(
    loader: DataLoader[Any], *, expected_samples: int, expected_batches: int
) -> dict[str, Any]:
    image_digest = _new_digest()
    target_digest = _new_digest()
    batch_sizes: list[int] = []
    samples = 0
    for images, targets in loader:
        if images.dtype != torch.float32 or targets.dtype != torch.int64:
            raise ValueError("unexpected batch dtype")
        if images.ndim != 4 or tuple(images.shape[1:]) != (3, 32, 32):
            raise ValueError(f"unexpected image batch shape: {tuple(images.shape)}")
        if not torch.isfinite(images).all().item():
            raise ValueError("non-finite transformed image")
        if targets.ndim != 1 or targets.shape[0] != images.shape[0]:
            raise ValueError("target/image batch mismatch")
        if targets.min().item() < 0 or targets.max().item() > 9:
            raise ValueError("target outside 0..9")
        batch_sizes.append(images.shape[0])
        samples += images.shape[0]
        _update_tensor_digest(image_digest, images)
        _update_tensor_digest(target_digest, targets)
    if samples != expected_samples:
        raise ValueError(f"expected {expected_samples} samples, observed {samples}")
    if (
        len(batch_sizes) != expected_batches
        or batch_sizes[0] != DIAGNOSTIC_BATCH_SIZE
        or batch_sizes[-1] != 16
    ):
        raise ValueError(f"unexpected batch partition: {batch_sizes}")
    return {
        "samples": samples,
        "batches": len(batch_sizes),
        "first_batch_size": batch_sizes[0],
        "last_batch_size": batch_sizes[-1],
        "transformed_images_sha256": image_digest.hexdigest().upper(),
        "targets_sha256": target_digest.hexdigest().upper(),
    }


def _candidate_request_digest() -> str:
    digest = _new_digest()
    sampler = CandidateCifar10EpochSampler(
        size=50_000,
        master_seed=DIAGNOSTIC_MASTER_SEED,
        epoch=DIAGNOSTIC_EPOCH,
    )
    seen: set[int] = set()
    for request in sampler:
        if not isinstance(request, AugmentedIndex):
            raise TypeError("candidate sampler emitted the wrong key type")
        if request.index in seen:
            raise ValueError(f"duplicate candidate index: {request.index}")
        seen.add(request.index)
        digest.update(request.index.to_bytes(4, "big"))
        digest.update(bytes([int(request.decision.horizontal_flip)]))
        digest.update(bytes([request.decision.crop_x, request.decision.crop_y]))
    if seen != set(range(50_000)):
        raise ValueError("candidate sampler is not a complete 50,000-index permutation")
    return digest.hexdigest().upper()


def _train_loader(dataset: Cifar10BinaryDataset, *, workers: int) -> DataLoader[Any]:
    kwargs: dict[str, Any] = {}
    if workers:
        kwargs["multiprocessing_context"] = "spawn"
    return DataLoader(
        dataset,
        batch_size=DIAGNOSTIC_BATCH_SIZE,
        sampler=CandidateCifar10EpochSampler(
            size=50_000,
            master_seed=DIAGNOSTIC_MASTER_SEED,
            epoch=DIAGNOSTIC_EPOCH,
        ),
        num_workers=workers,
        drop_last=False,
        generator=torch.Generator().manual_seed(DIAGNOSTIC_WORKER_GENERATOR_SEED),
        **kwargs,
    )


def _run_train(prepared: Path, workers: int) -> dict[str, Any]:
    dataset = Cifar10BinaryDataset(prepared, split="train")
    try:
        return _loader_report(
            _train_loader(dataset, workers=workers),
            expected_samples=50_000,
            expected_batches=782,
        )
    finally:
        dataset.close()


def _run_test(prepared: Path) -> dict[str, Any]:
    dataset = Cifar10BinaryDataset(prepared, split="test")
    try:
        loader = DataLoader(
            dataset,
            batch_size=DIAGNOSTIC_BATCH_SIZE,
            sampler=SequentialSampler(dataset),
            num_workers=0,
            drop_last=False,
            generator=torch.Generator().manual_seed(
                DIAGNOSTIC_WORKER_GENERATOR_SEED
            ),
        )
        return _loader_report(loader, expected_samples=10_000, expected_batches=157)
    finally:
        dataset.close()


def run_diagnostic(
    *, lock_path: Path, binary_archive: Path, prepared: Path
) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    binary_lock = lock["artifacts"]["toronto_binary"]
    if binary_lock["md5"].lower() != CIFAR10_TORONTO_BINARY_MD5:
        raise ValueError("binary lock does not match the official Toronto MD5")
    artifact_identity = verify_file_identity(
        binary_archive,
        expected_md5=binary_lock["md5"],
        expected_sha256=binary_lock["sha256"],
    )
    verified_prepared = prepare_cifar10_binary_archive(
        binary_archive,
        prepared.parent,
        expected_md5=binary_lock["md5"],
        expected_sha256=binary_lock["sha256"],
    )
    if verified_prepared.resolve() != prepared.resolve():
        raise ValueError(
            f"prepared path mismatch: {verified_prepared} != {prepared}"
        )
    prepared_manifest = prepared / "prepared-manifest.json"
    if not prepared_manifest.is_file():
        raise FileNotFoundError(f"prepared manifest missing: {prepared_manifest}")

    request_digest = _candidate_request_digest()
    zero_workers = _run_train(prepared, 0)
    two_workers = _run_train(prepared, 2)
    replay_fields = (
        "samples",
        "batches",
        "first_batch_size",
        "last_batch_size",
        "transformed_images_sha256",
        "targets_sha256",
    )
    worker_count_bit_exact = all(
        zero_workers[field] == two_workers[field] for field in replay_fields
    )
    if not worker_count_bit_exact:
        raise ValueError("zero-worker and two-worker train epochs differ")

    return {
        "classification": "PHASE2-DATA-PIPELINE-DIAGNOSTIC-NOT-FORMAL-FREEZE",
        "evidence_class": "DERIVED",
        "record_date": date.today().isoformat(),
        "project_git": _git_state(),
        "optimizer_constructed": False,
        "optimizer_steps": 0,
        "model_constructed": False,
        "accuracy_computed": False,
        "artifact": artifact_identity,
        "prepared_manifest": {
            "path": str(prepared_manifest.resolve()),
            "sha256": file_digest(prepared_manifest, "sha256"),
        },
        "candidate_h003_mapping": {
            "approved": False,
            "stream_domain": CIFAR10_CANDIDATE_STREAM_DOMAIN,
            "stream_derivation": "first 8 SHA256 bytes as big-endian integer, masked to 63 bits",
            "master_seed": DIAGNOSTIC_MASTER_SEED,
            "epoch": DIAGNOSTIC_EPOCH,
            "batch_size": DIAGNOSTIC_BATCH_SIZE,
            "worker_generator_seed": DIAGNOSTIC_WORKER_GENERATOR_SEED,
            "request_order_and_decisions_sha256": request_digest,
        },
        "train_zero_workers": zero_workers,
        "train_two_workers": two_workers,
        "worker_count_bit_exact": worker_count_bit_exact,
        "test_normalization_only_zero_workers": _run_test(prepared),
        "torch": {
            "version": torch.__version__,
            "python_threads": torch.get_num_threads(),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--binary-archive", type=Path, default=DEFAULT_BINARY_ARCHIVE)
    parser.add_argument("--prepared", type=Path, default=DEFAULT_PREPARED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_diagnostic(
        lock_path=args.lock,
        binary_archive=args.binary_archive,
        prepared=args.prepared,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
