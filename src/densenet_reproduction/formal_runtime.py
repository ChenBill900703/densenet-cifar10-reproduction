"""Frozen formal execution adapter; Phase 5 may only static/mock-test it."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .phase5 import (
    AppendOnlyAttemptLedger,
    LaunchIdentity,
    PHASE5_PROJECT_SEEDS,
    Phase6Authorization,
    require_phase6_authorization,
    validate_launch_identity,
)


@dataclass(frozen=True, slots=True)
class FormalStepCoordinates:
    master_seed: int
    epoch: int
    batch_index: int
    accepted_step: int


def execute_accounted_optimizer_call(
    *,
    coordinates: FormalStepCoordinates,
    ledger: AppendOnlyAttemptLedger,
    optimizer_call: Callable[[], None],
    authorization: Phase6Authorization,
    expected_launch: LaunchIdentity,
    observed_launch: LaunchIdentity,
) -> None:
    """Durably record intent, call once, then durably record completion.

    Tests supply a plain callback, never a torch optimizer. If the callback
    raises or the process dies, the intent remains unresolved by construction.
    """

    validate_launch_identity(expected_launch, observed_launch)
    require_phase6_authorization(
        authorization,
        expected_freeze_manifest_sha256=expected_launch.freeze_manifest_sha256,
    )
    intent = ledger.append_intent(
        master_seed=coordinates.master_seed,
        epoch=coordinates.epoch,
        batch_index=coordinates.batch_index,
        accepted_step=coordinates.accepted_step,
    )
    optimizer_call()
    ledger.append_completion(intent)


def require_create_new_formal_run_root(
    runs_root: Path, freeze_manifest_sha256: str, master_seed: int
) -> Path:
    """Create the approved full-manifest-hash seed path without overwrite."""

    from .phase5 import _uppercase_sha256

    digest = _uppercase_sha256(freeze_manifest_sha256, "freeze_manifest_sha256")
    if master_seed not in PHASE5_PROJECT_SEEDS:
        raise ValueError("Formal run seed is not approved.")
    root = runs_root.resolve(strict=True)
    if not root.is_dir() or runs_root.is_symlink():
        raise ValueError("runs_root must be a regular directory.")
    require_formal_seed_training_order(
        root,
        digest,
        master_seed,
        resuming=False,
    )
    target = root / digest / f"seed-{master_seed}"
    target.mkdir(parents=True, exist_ok=False)
    return target


def _require_completed_formal_seed(
    seed_root: Path,
    freeze_manifest_sha256: str,
    master_seed: int,
    *,
    allow_final_test_evidence: bool = False,
) -> None:
    from .formal_checkpoint import read_formal_checkpoint_manifest

    if seed_root.is_symlink() or not seed_root.is_dir():
        raise RuntimeError("Earlier formal seed directory is missing or unsafe.")
    if not allow_final_test_evidence and any(
        candidate.name.startswith("final-test-") for candidate in seed_root.iterdir()
    ):
        raise RuntimeError("Final-test evidence exists before all seed training completed.")
    final_manifest = None
    for epoch in range(1, 301):
        checkpoint = seed_root / f"epoch-{epoch:03d}.pt"
        manifest = read_formal_checkpoint_manifest(checkpoint)
        if (
            manifest["completed_epoch"] != epoch
            or manifest["master_seed"] != master_seed
            or manifest["accepted_trajectory_steps"] != epoch * 782
            or manifest["provenance"]["freeze_manifest_sha256"]
            != freeze_manifest_sha256
        ):
            raise RuntimeError("Earlier formal seed checkpoint set is incomplete.")
        final_manifest = manifest
    ledger = AppendOnlyAttemptLedger(
        seed_root / "optimizer-attempts.jsonl", create=False
    )
    summary = ledger.summary()
    if summary.unresolved_intents or summary.completed_calls < 234_600:
        raise RuntimeError("Earlier formal seed attempt ledger is incomplete.")
    if final_manifest is None or not ledger.records:
        raise RuntimeError("Earlier formal seed has no final provenance.")
    if (
        final_manifest["provenance"]["ledger_head_sha256"]
        != ledger.records[-1]["record_sha256"]
        or final_manifest["physical_optimizer_call_lower_bound"]
        != summary.physical_call_lower_bound
        or final_manifest["physical_optimizer_call_upper_bound"]
        != summary.physical_call_upper_bound
    ):
        raise RuntimeError("Earlier formal seed ledger/checkpoint provenance differs.")


def require_formal_seed_training_order(
    formal_root: Path,
    freeze_manifest_sha256: str,
    master_seed: int,
    *,
    resuming: bool,
) -> Path:
    """Fail before formal mutation unless the frozen seed order is satisfied."""

    from .phase5 import _uppercase_sha256

    if master_seed not in PHASE5_PROJECT_SEEDS:
        raise ValueError("Formal run seed is not approved.")
    digest = _uppercase_sha256(freeze_manifest_sha256, "freeze_manifest_sha256")
    root = formal_root.resolve(strict=True)
    if formal_root.is_symlink() or not root.is_dir():
        raise ValueError("formal_root must be a regular directory.")
    freeze_root = root / digest
    seed_index = PHASE5_PROJECT_SEEDS.index(master_seed)
    for earlier_seed in PHASE5_PROJECT_SEEDS[:seed_index]:
        _require_completed_formal_seed(
            freeze_root / f"seed-{earlier_seed}", digest, earlier_seed
        )
    for later_seed in PHASE5_PROJECT_SEEDS[seed_index + 1 :]:
        later = freeze_root / f"seed-{later_seed}"
        if later.exists() or later.is_symlink():
            raise RuntimeError("A later formal seed has already started out of order.")
    current = freeze_root / f"seed-{master_seed}"
    if resuming:
        resolved = current.resolve(strict=True)
        if current.is_symlink() or not resolved.is_dir():
            raise RuntimeError("Formal resume seed directory is missing or unsafe.")
        return resolved
    if current.exists() or current.is_symlink():
        raise FileExistsError(f"Formal seed directory already exists: {current}")
    return current
