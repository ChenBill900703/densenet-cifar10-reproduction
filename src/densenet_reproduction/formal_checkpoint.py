"""Formal epoch-boundary checkpoint schema and Phase 5 structural fixture.

The save/load APIs are frozen runtime code for a later authorized Phase 6 run.
Phase 5 tests exercise only validation and a distinctly classified structural
size fixture; they never perform a model forward or optimizer step.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import random
import tempfile
from typing import Any, Final

import torch

from .checkpoint import (
    _capture_rng,
    _model_metadata,
    _parameter_names,
    _require_existing_regular_file,
    _require_new_regular_target,
    _resolve_target,
    _validate_model_state,
    _validate_optimizer_state,
    _validate_rng_state,
)
from .mechanics import (
    build_phase3_optimizer,
    build_project_seeded_model,
    require_project_master_seed,
    validate_phase3_optimizer,
)
from .model import DenseNetBC100Cifar10
from .phase5 import AttemptSummary, canonical_json_bytes, sha256_file


FORMAL_CHECKPOINT_SCHEMA_VERSION: Final[int] = 1
FORMAL_CHECKPOINT_CLASSIFICATION: Final[str] = "FORMAL-EPOCH-CHECKPOINT-V1"
FORMAL_CHECKPOINT_MANIFEST_CLASSIFICATION: Final[str] = (
    "FORMAL-EPOCH-CHECKPOINT-MANIFEST-V1"
)
STRUCTURAL_FIXTURE_CLASSIFICATION: Final[str] = (
    "PHASE5-STRUCTURAL-CHECKPOINT-SIZE-FIXTURE-NO-OPTIMIZER-STEP"
)


@dataclass(frozen=True, slots=True)
class FormalCheckpointProvenance:
    freeze_manifest_sha256: str
    source_commit: str
    project_wheel_sha256: str
    environment_manifest_sha256: str
    dataset_sha256: str
    config_sha256: str
    ledger_head_sha256: str

    def __post_init__(self) -> None:
        from .phase5 import _HEX40, _uppercase_sha256

        if not _HEX40.fullmatch(self.source_commit):
            raise ValueError("source_commit must be a full Git SHA1.")
        for field in (
            "freeze_manifest_sha256",
            "project_wheel_sha256",
            "environment_manifest_sha256",
            "dataset_sha256",
            "config_sha256",
            "ledger_head_sha256",
        ):
            _uppercase_sha256(getattr(self, field), field)


@dataclass(frozen=True, slots=True)
class FormalCheckpointLoadResult:
    completed_epoch: int
    next_epoch: int
    master_seed: int
    accepted_trajectory_steps: int
    physical_call_lower_bound: int
    physical_call_upper_bound: int
    checkpoint_sha256: str


def _validate_progress(completed_epoch: int, summary: AttemptSummary) -> int:
    if isinstance(completed_epoch, bool) or not isinstance(completed_epoch, int):
        raise ValueError("completed_epoch must be a plain integer.")
    if not 1 <= completed_epoch <= 300:
        raise ValueError("completed_epoch must be in [1, 300].")
    accepted = completed_epoch * 782
    if summary.unresolved_intents != 0:
        raise ValueError("An epoch checkpoint cannot contain an unresolved intent.")
    if summary.completed_calls < accepted:
        raise ValueError("Physical completed calls cannot be below accepted trajectory steps.")
    if summary.physical_call_lower_bound != summary.completed_calls:
        raise ValueError("Clean checkpoint physical lower bound is invalid.")
    if summary.physical_call_upper_bound != summary.completed_calls:
        raise ValueError("Clean checkpoint physical upper bound is invalid.")
    return accepted


def _formal_payload(
    *,
    model: DenseNetBC100Cifar10,
    optimizer: torch.optim.Optimizer,
    completed_epoch: int,
    master_seed: int,
    attempt_summary: AttemptSummary,
    provenance: FormalCheckpointProvenance,
    cuda_device_indices: tuple[int, ...],
) -> dict[str, Any]:
    seed = require_project_master_seed(master_seed)
    accepted = _validate_progress(completed_epoch, attempt_summary)
    validate_phase3_optimizer(model, optimizer)
    optimizer_state = optimizer.state_dict()
    _validate_optimizer_state(optimizer_state, model, completed_epoch=completed_epoch)
    return {
        "accepted_trajectory_steps": accepted,
        "classification": FORMAL_CHECKPOINT_CLASSIFICATION,
        "completed_epoch": completed_epoch,
        "master_seed": seed,
        "model_metadata": _model_metadata(model),
        "model_state": model.state_dict(),
        "next_epoch": completed_epoch + 1,
        "optimizer_state": optimizer_state,
        "parameter_names": _parameter_names(model),
        "physical_optimizer_call_lower_bound": attempt_summary.physical_call_lower_bound,
        "physical_optimizer_call_upper_bound": attempt_summary.physical_call_upper_bound,
        "provenance": asdict(provenance),
        "rng_state": _capture_rng(cuda_device_indices),
        "schema_version": FORMAL_CHECKPOINT_SCHEMA_VERSION,
        "test_records_accessed": 0,
    }


def save_formal_checkpoint(
    *,
    checkpoint_path: Path,
    allowed_root: Path,
    model: DenseNetBC100Cifar10,
    optimizer: torch.optim.Optimizer,
    completed_epoch: int,
    master_seed: int,
    attempt_summary: AttemptSummary,
    provenance: FormalCheckpointProvenance,
    cuda_device_indices: tuple[int, ...] = (0,),
) -> dict[str, Any]:
    target, _ = _resolve_target(checkpoint_path, allowed_root)
    manifest_path = target.with_name(f"{target.name}.manifest.json")
    _require_new_regular_target(target)
    _require_new_regular_target(manifest_path)
    payload = _formal_payload(
        model=model,
        optimizer=optimizer,
        completed_epoch=completed_epoch,
        master_seed=master_seed,
        attempt_summary=attempt_summary,
        provenance=provenance,
        cuda_device_indices=cuda_device_indices,
    )
    reserved_target = False
    reserved_manifest = False
    temporary: Path | None = None
    try:
        descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        reserved_target = True
        descriptor = os.open(
            manifest_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
        )
        os.close(descriptor)
        reserved_manifest = True
        descriptor, name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        os.close(descriptor)
        temporary = Path(name)
        torch.save(payload, temporary)
        with temporary.open("rb+") as stream:
            os.fsync(stream.fileno())
        checkpoint_hash = sha256_file(temporary)
        os.replace(temporary, target)
        temporary = None
        manifest = {
            "accepted_trajectory_steps": payload["accepted_trajectory_steps"],
            "artifact": target.name,
            "bytes": target.stat().st_size,
            "classification": FORMAL_CHECKPOINT_MANIFEST_CLASSIFICATION,
            "completed_epoch": completed_epoch,
            "evidence_class": "FORMAL-REPRODUCTION-RESULT",
            "master_seed": master_seed,
            "physical_optimizer_call_lower_bound": payload[
                "physical_optimizer_call_lower_bound"
            ],
            "physical_optimizer_call_upper_bound": payload[
                "physical_optimizer_call_upper_bound"
            ],
            "provenance": asdict(provenance),
            "sha256": checkpoint_hash,
        }
        manifest_bytes = canonical_json_bytes(manifest)
        # Replace the reserved empty manifest only through a fully fsynced temp.
        descriptor, name = tempfile.mkstemp(
            prefix=f".{manifest_path.name}.", suffix=".tmp", dir=manifest_path.parent
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(manifest_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        temporary = Path(name)
        os.replace(temporary, manifest_path)
        temporary = None
        return manifest
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        if reserved_target:
            target.unlink(missing_ok=True)
        if reserved_manifest:
            manifest_path.unlink(missing_ok=True)
        raise


def _load_manifest(target: Path) -> dict[str, Any]:
    path = target.with_name(f"{target.name}.manifest.json")
    _require_existing_regular_file(path)
    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Formal checkpoint manifest is invalid JSON.") from error
    if raw != canonical_json_bytes(document):
        raise ValueError("Formal checkpoint manifest is not canonical JSON.")
    expected = {
        "accepted_trajectory_steps",
        "artifact",
        "bytes",
        "classification",
        "completed_epoch",
        "evidence_class",
        "master_seed",
        "physical_optimizer_call_lower_bound",
        "physical_optimizer_call_upper_bound",
        "provenance",
        "sha256",
    }
    if not isinstance(document, dict) or set(document) != expected:
        raise ValueError("Unexpected formal checkpoint manifest schema.")
    if document["classification"] != FORMAL_CHECKPOINT_MANIFEST_CLASSIFICATION:
        raise ValueError("Formal checkpoint manifest classification mismatch.")
    if document["evidence_class"] != "FORMAL-REPRODUCTION-RESULT":
        raise ValueError("Formal checkpoint evidence classification mismatch.")
    if document["artifact"] != target.name or document["bytes"] != target.stat().st_size:
        raise ValueError("Formal checkpoint manifest identity mismatch.")
    if document["sha256"] != sha256_file(target):
        raise ValueError("Formal checkpoint SHA256 mismatch.")
    FormalCheckpointProvenance(**document["provenance"])
    return document


def read_formal_checkpoint_manifest(checkpoint_path: Path) -> dict[str, Any]:
    _require_existing_regular_file(checkpoint_path)
    return _load_manifest(checkpoint_path)


def load_formal_checkpoint(
    *,
    checkpoint_path: Path,
    allowed_root: Path,
    model: DenseNetBC100Cifar10,
    optimizer: torch.optim.Optimizer,
    expected_master_seed: int,
    expected_provenance: FormalCheckpointProvenance,
    expected_cuda_device_indices: tuple[int, ...] = (0,),
) -> FormalCheckpointLoadResult:
    target, _ = _resolve_target(checkpoint_path, allowed_root)
    _require_existing_regular_file(target)
    manifest = _load_manifest(target)
    payload = torch.load(target, map_location="cpu", weights_only=True)
    expected_keys = {
        "accepted_trajectory_steps",
        "classification",
        "completed_epoch",
        "master_seed",
        "model_metadata",
        "model_state",
        "next_epoch",
        "optimizer_state",
        "parameter_names",
        "physical_optimizer_call_lower_bound",
        "physical_optimizer_call_upper_bound",
        "provenance",
        "rng_state",
        "schema_version",
        "test_records_accessed",
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise ValueError("Unexpected formal checkpoint payload schema.")
    if payload["schema_version"] != FORMAL_CHECKPOINT_SCHEMA_VERSION:
        raise ValueError("Formal checkpoint schema version mismatch.")
    if payload["classification"] != FORMAL_CHECKPOINT_CLASSIFICATION:
        raise ValueError("Formal checkpoint classification mismatch.")
    epoch = payload["completed_epoch"]
    if payload["next_epoch"] != epoch + 1 or not 1 <= epoch <= 300:
        raise ValueError("Formal checkpoint epoch cursor mismatch.")
    if payload["accepted_trajectory_steps"] != epoch * 782:
        raise ValueError("Formal checkpoint accepted-step count mismatch.")
    if payload["test_records_accessed"] != 0:
        raise ValueError("Training checkpoint records forbidden test access.")
    if payload["master_seed"] != require_project_master_seed(expected_master_seed):
        raise ValueError("Formal checkpoint master seed mismatch.")
    if payload["provenance"] != asdict(expected_provenance):
        raise ValueError("Formal checkpoint provenance mismatch.")
    if payload["parameter_names"] != _parameter_names(model):
        raise ValueError("Formal checkpoint parameter order mismatch.")
    if payload["model_metadata"] != _model_metadata(model):
        raise ValueError("Formal checkpoint model metadata mismatch.")
    _validate_model_state(payload["model_state"], model)
    _validate_optimizer_state(payload["optimizer_state"], model, completed_epoch=epoch)
    _validate_rng_state(payload["rng_state"], expected_cuda_device_indices)
    validate_phase3_optimizer(model, optimizer)
    for field in (
        "accepted_trajectory_steps",
        "completed_epoch",
        "master_seed",
        "physical_optimizer_call_lower_bound",
        "physical_optimizer_call_upper_bound",
    ):
        if manifest[field] != payload[field]:
            raise ValueError(f"Formal checkpoint manifest/payload {field} mismatch.")
    if manifest["provenance"] != payload["provenance"]:
        raise ValueError("Formal checkpoint manifest/payload provenance mismatch.")
    # All checks precede mutation.
    model.load_state_dict(payload["model_state"], strict=True)
    optimizer.load_state_dict(payload["optimizer_state"])
    validate_phase3_optimizer(model, optimizer)
    random.setstate(payload["rng_state"]["python"])
    torch.random.set_rng_state(payload["rng_state"]["torch_cpu"])
    for entry in payload["rng_state"]["torch_cuda"]:
        torch.cuda.set_rng_state(entry["state"], device=entry["device_index"])
    return FormalCheckpointLoadResult(
        completed_epoch=epoch,
        next_epoch=epoch + 1,
        master_seed=payload["master_seed"],
        accepted_trajectory_steps=payload["accepted_trajectory_steps"],
        physical_call_lower_bound=payload["physical_optimizer_call_lower_bound"],
        physical_call_upper_bound=payload["physical_optimizer_call_upper_bound"],
        checkpoint_sha256=manifest["sha256"],
    )


def write_structural_checkpoint_size_fixture(path: Path) -> int:
    """Write a schema-faithful shape fixture without forward/backward/step."""

    model = build_project_seeded_model(1021082110)
    optimizer = build_phase3_optimizer(model, epoch=1)
    for parameter in model.parameters():
        if parameter.requires_grad:
            optimizer.state[parameter]["momentum_buffer"] = torch.zeros_like(parameter)
    payload = {
        "accepted_trajectory_steps": 782,
        "classification": STRUCTURAL_FIXTURE_CLASSIFICATION,
        "completed_epoch": 1,
        "master_seed": 1021082110,
        "model_metadata": _model_metadata(model),
        "model_state": model.state_dict(),
        "next_epoch": 2,
        "optimizer_state": optimizer.state_dict(),
        "parameter_names": _parameter_names(model),
        "physical_optimizer_call_lower_bound": 782,
        "physical_optimizer_call_upper_bound": 782,
        "provenance": {
            "classification": STRUCTURAL_FIXTURE_CLASSIFICATION,
            "not_a_formal_checkpoint": True,
        },
        "rng_state": _capture_rng(()),
        "schema_version": FORMAL_CHECKPOINT_SCHEMA_VERSION,
        "test_records_accessed": 0,
    }
    _require_new_regular_target(path)
    torch.save(payload, path)
    return path.stat().st_size
