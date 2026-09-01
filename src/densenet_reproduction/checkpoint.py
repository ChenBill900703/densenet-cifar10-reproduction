"""Fail-closed Phase 3 epoch-boundary checkpoint primitives.

The schema stores synthetic-mechanics state for validation and is designed for
the later formal epoch-boundary policy.  It never stores accuracy, a best-model
field, or a nonzero formal optimizer-step count.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import random
import re
import tempfile
from typing import Any, Final

import torch
from torch import Tensor

from .mechanics import (
    LOSS_POLICY_ID,
    LR_POLICY_ID,
    OPTIMIZER_POLICY_ID,
    RNG_POLICY_ID,
    SYNTHETIC_CLASSIFICATION,
    SyntheticStepLedger,
    learning_rate_for_epoch,
    require_project_master_seed,
    validate_phase3_optimizer,
)
from .model import DenseNetBC100Cifar10


CHECKPOINT_SCHEMA_VERSION: Final[int] = 1
CHECKPOINT_CLASSIFICATION: Final[str] = (
    "PHASE3-EPOCH-CHECKPOINT-NOT-FORMAL-RUN"
)
CHECKPOINT_POLICY_ID: Final[str] = "densenet-epoch-boundary-checkpoint-v1"
MANIFEST_CLASSIFICATION: Final[str] = "PHASE3-CHECKPOINT-MANIFEST"

_HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True, slots=True)
class CheckpointProvenance:
    """Hashes that a resume must match before any state is mutated."""

    source_commit: str
    environment_lock_sha256: str
    dataset_sha256: str
    config_sha256: str

    def __post_init__(self) -> None:
        if not _HEX40.fullmatch(self.source_commit):
            raise ValueError("source_commit must be a full 40-character Git hash.")
        object.__setattr__(self, "source_commit", self.source_commit.lower())
        for field_name in (
            "environment_lock_sha256",
            "dataset_sha256",
            "config_sha256",
        ):
            value = getattr(self, field_name)
            if not _HEX64.fullmatch(value):
                raise ValueError(f"{field_name} must be a 64-character SHA256.")
            object.__setattr__(self, field_name, value.upper())


@dataclass(frozen=True, slots=True)
class CheckpointLoadResult:
    completed_epoch: int
    next_epoch: int
    master_seed: int
    synthetic_optimizer_steps: int
    formal_optimizer_steps: int
    checkpoint_sha256: str


def _policy_ids() -> dict[str, str]:
    return {
        "checkpoint": CHECKPOINT_POLICY_ID,
        "loss": LOSS_POLICY_ID,
        "lr": LR_POLICY_ID,
        "optimizer": OPTIMIZER_POLICY_ID,
        "rng": RNG_POLICY_ID,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _manifest_path(checkpoint_path: Path) -> Path:
    return checkpoint_path.with_name(f"{checkpoint_path.name}.manifest.json")


def _resolve_target(path: Path, allowed_root: Path) -> tuple[Path, Path]:
    if not isinstance(path, Path) or not isinstance(allowed_root, Path):
        raise TypeError("checkpoint_path and allowed_root must be pathlib.Path values.")
    root = allowed_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("allowed_root must be a directory.")
    parent = path.parent.resolve(strict=True)
    try:
        parent.relative_to(root)
    except ValueError as error:
        raise ValueError("Checkpoint path escapes the allowed root.") from error
    if path.name in ("", ".", "..") or path.suffix != ".pt":
        raise ValueError("Checkpoint filename must end in .pt.")
    return parent / path.name, root


def _require_new_regular_target(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Immutable checkpoint target already exists: {path}")


def _reserve_immutable_target(path: Path) -> None:
    """Atomically reserve a new name so the later replace cannot overwrite history."""

    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)


def _require_existing_regular_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular non-symlink file: {path}")


def _model_metadata(model: DenseNetBC100Cifar10) -> dict[str, dict[str, Any]]:
    return {
        name: {"dtype": str(tensor.dtype), "shape": list(tensor.shape)}
        for name, tensor in model.state_dict().items()
    }


def _parameter_names(model: DenseNetBC100Cifar10) -> list[str]:
    names = [name for name, parameter in model.named_parameters() if parameter.requires_grad]
    if len(names) != 299 or len(set(names)) != 299:
        raise ValueError("Checkpoint requires 299 unique trainable parameter names.")
    return names


def _capture_rng(cuda_device_indices: tuple[int, ...]) -> dict[str, Any]:
    if len(set(cuda_device_indices)) != len(cuda_device_indices):
        raise ValueError("cuda_device_indices must be unique.")
    cuda_states: list[dict[str, Any]] = []
    if cuda_device_indices:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA RNG capture requested but CUDA is unavailable.")
        for index in cuda_device_indices:
            if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                raise ValueError("CUDA device indices must be non-negative integers.")
            if index >= torch.cuda.device_count():
                raise ValueError(f"CUDA device index {index} is unavailable.")
            cuda_states.append(
                {"device_index": index, "state": torch.cuda.get_rng_state(index).cpu()}
            )
    return {
        "python": random.getstate(),
        "torch_cpu": torch.random.get_rng_state().cpu(),
        "torch_cuda": cuda_states,
    }


def _validate_optimizer_state(
    optimizer_state: dict[str, Any],
    model: DenseNetBC100Cifar10,
    *,
    completed_epoch: int,
) -> None:
    if set(optimizer_state) != {"state", "param_groups"}:
        raise ValueError("Unexpected optimizer state schema.")
    groups = optimizer_state["param_groups"]
    if not isinstance(groups, list) or len(groups) != 1:
        raise ValueError("Checkpoint optimizer must have one parameter group.")
    group = groups[0]
    expected_group_keys = {
        "dampening",
        "differentiable",
        "foreach",
        "fused",
        "lr",
        "maximize",
        "momentum",
        "nesterov",
        "params",
        "weight_decay",
    }
    if set(group) != expected_group_keys:
        raise ValueError("Unexpected optimizer parameter-group schema.")
    expected_settings = {
        "lr": learning_rate_for_epoch(completed_epoch),
        "momentum": 0.9,
        "dampening": 0.0,
        "weight_decay": 1e-4,
        "nesterov": True,
        "maximize": False,
        "foreach": False,
        "differentiable": False,
        "fused": False,
    }
    for key, expected in expected_settings.items():
        if group.get(key) != expected:
            raise ValueError(f"Checkpoint optimizer setting {key} is invalid.")
    parameter_ids = group.get("params")
    if parameter_ids != list(range(299)):
        raise ValueError("Checkpoint optimizer parameter IDs/order are invalid.")
    state = optimizer_state["state"]
    if not isinstance(state, dict) or set(state) != set(range(299)):
        raise ValueError("Checkpoint must contain all 299 momentum states.")
    parameters = [value for value in model.parameters() if value.requires_grad]
    for index, parameter in enumerate(parameters):
        entry = state[index]
        if set(entry) != {"momentum_buffer"}:
            raise ValueError("Unexpected per-parameter optimizer state.")
        buffer = entry["momentum_buffer"]
        if not isinstance(buffer, Tensor):
            raise ValueError("Momentum buffer must be a tensor.")
        if buffer.shape != parameter.shape or buffer.dtype != parameter.dtype:
            raise ValueError("Momentum buffer tensor metadata mismatch.")
        if not bool(torch.isfinite(buffer).all()):
            raise ValueError("Momentum buffer contains non-finite values.")


def _validate_model_state(
    candidate: dict[str, Tensor], model: DenseNetBC100Cifar10
) -> None:
    expected = model.state_dict()
    if list(candidate) != list(expected):
        raise ValueError("Checkpoint model state names/order do not match.")
    for name, reference in expected.items():
        value = candidate[name]
        if not isinstance(value, Tensor):
            raise ValueError(f"Model state {name} is not a tensor.")
        if value.shape != reference.shape or value.dtype != reference.dtype:
            raise ValueError(f"Model state metadata mismatch for {name}.")
        if not bool(torch.isfinite(value).all()):
            raise ValueError(f"Model state contains non-finite values: {name}.")


def _validate_rng_state(
    rng_state: dict[str, Any], expected_cuda_device_indices: tuple[int, ...]
) -> None:
    if set(rng_state) != {"python", "torch_cpu", "torch_cuda"}:
        raise ValueError("Unexpected RNG state schema.")
    python_state = rng_state["python"]
    if not isinstance(python_state, tuple):
        raise ValueError("Python RNG state must be a tuple.")
    try:
        random.Random().setstate(python_state)
    except (TypeError, ValueError) as error:
        raise ValueError("Python RNG state is invalid.") from error
    cpu_state = rng_state["torch_cpu"]
    if not isinstance(cpu_state, Tensor) or cpu_state.dtype is not torch.uint8:
        raise ValueError("PyTorch CPU RNG state is invalid.")
    try:
        torch.Generator(device="cpu").set_state(cpu_state)
    except RuntimeError as error:
        raise ValueError("PyTorch CPU RNG state is invalid.") from error
    cuda_states = rng_state["torch_cuda"]
    if not isinstance(cuda_states, list):
        raise ValueError("PyTorch CUDA RNG state must be a list.")
    observed_indices: list[int] = []
    for entry in cuda_states:
        if set(entry) != {"device_index", "state"}:
            raise ValueError("Unexpected CUDA RNG state entry.")
        index = entry["device_index"]
        state = entry["state"]
        if isinstance(index, bool) or not isinstance(index, int):
            raise ValueError("CUDA RNG device index is invalid.")
        if not isinstance(state, Tensor) or state.dtype is not torch.uint8:
            raise ValueError("CUDA RNG tensor is invalid.")
        if not torch.cuda.is_available() or index >= torch.cuda.device_count():
            raise ValueError("CUDA RNG device index is unavailable.")
        try:
            torch.Generator(device=f"cuda:{index}").set_state(state)
        except RuntimeError as error:
            raise ValueError("CUDA RNG tensor is invalid.") from error
        observed_indices.append(index)
    if tuple(observed_indices) != expected_cuda_device_indices:
        raise ValueError("CUDA RNG device list does not match the resume request.")


def _payload(
    *,
    model: DenseNetBC100Cifar10,
    optimizer: torch.optim.Optimizer,
    ledger: SyntheticStepLedger,
    completed_epoch: int,
    master_seed: int,
    provenance: CheckpointProvenance,
    cuda_device_indices: tuple[int, ...],
) -> dict[str, Any]:
    if isinstance(completed_epoch, bool) or not isinstance(completed_epoch, int):
        raise TypeError("completed_epoch must be an integer.")
    if not 1 <= completed_epoch <= 300:
        raise ValueError("completed_epoch must be in [1, 300].")
    seed = require_project_master_seed(master_seed)
    if ledger.formal_optimizer_steps != 0 or ledger.synthetic_optimizer_steps <= 0:
        raise ValueError("Checkpoint requires synthetic steps and zero formal steps.")
    validate_phase3_optimizer(model, optimizer)
    optimizer_state = optimizer.state_dict()
    _validate_optimizer_state(optimizer_state, model, completed_epoch=completed_epoch)
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "classification": CHECKPOINT_CLASSIFICATION,
        "synthetic_classification": SYNTHETIC_CLASSIFICATION,
        "formal_optimizer_steps": 0,
        "synthetic_optimizer_steps": ledger.synthetic_optimizer_steps,
        "completed_epoch": completed_epoch,
        "next_epoch": completed_epoch + 1,
        "master_seed": seed,
        "policy_ids": _policy_ids(),
        "provenance": asdict(provenance),
        "parameter_names": _parameter_names(model),
        "model_metadata": _model_metadata(model),
        "model_state": model.state_dict(),
        "optimizer_state": optimizer_state,
        "rng_state": _capture_rng(cuda_device_indices),
    }


def save_phase3_checkpoint(
    *,
    checkpoint_path: Path,
    allowed_root: Path,
    model: DenseNetBC100Cifar10,
    optimizer: torch.optim.Optimizer,
    ledger: SyntheticStepLedger,
    completed_epoch: int,
    master_seed: int,
    provenance: CheckpointProvenance,
    cuda_device_indices: tuple[int, ...] = (),
) -> dict[str, Any]:
    """Atomically save one immutable checkpoint plus its strict JSON manifest."""

    target, _ = _resolve_target(checkpoint_path, allowed_root)
    manifest_target = _manifest_path(target)
    _require_new_regular_target(target)
    _require_new_regular_target(manifest_target)
    payload = _payload(
        model=model,
        optimizer=optimizer,
        ledger=ledger,
        completed_epoch=completed_epoch,
        master_seed=master_seed,
        provenance=provenance,
        cuda_device_indices=cuda_device_indices,
    )
    checkpoint_temp: Path | None = None
    manifest_temp: Path | None = None
    checkpoint_reserved = False
    manifest_reserved = False
    try:
        _reserve_immutable_target(target)
        checkpoint_reserved = True
        _reserve_immutable_target(manifest_target)
        manifest_reserved = True
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        os.close(descriptor)
        checkpoint_temp = Path(temporary_name)
        torch.save(payload, checkpoint_temp)
        # Windows requires a writable descriptor for FlushFileBuffers, which
        # backs os.fsync.  Reopen without modifying the completed payload.
        with checkpoint_temp.open("rb+") as stream:
            os.fsync(stream.fileno())
        checkpoint_sha256 = _sha256_file(checkpoint_temp)
        manifest = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "classification": MANIFEST_CLASSIFICATION,
            "evidence_class": "DERIVED",
            "artifact": target.name,
            "bytes": checkpoint_temp.stat().st_size,
            "sha256": checkpoint_sha256,
            "formal_optimizer_steps": 0,
            "synthetic_optimizer_steps": ledger.synthetic_optimizer_steps,
        }
        manifest_bytes = (
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{manifest_target.name}.", suffix=".tmp", dir=target.parent
        )
        manifest_temp = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(manifest_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(checkpoint_temp, target)
        checkpoint_temp = None
        os.replace(manifest_temp, manifest_target)
        manifest_temp = None
        return manifest
    except BaseException:
        for temporary in (checkpoint_temp, manifest_temp):
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        # A crash/failure between the two atomic replacements is incomplete and
        # therefore not loadable. Remove only names reserved by this call.
        if checkpoint_reserved:
            target.unlink(missing_ok=True)
        if manifest_reserved:
            manifest_target.unlink(missing_ok=True)
        raise


def _load_manifest(target: Path) -> dict[str, Any]:
    manifest_path = _manifest_path(target)
    _require_existing_regular_file(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Checkpoint manifest is not valid UTF-8 JSON.") from error
    if not isinstance(manifest, dict):
        raise ValueError("Checkpoint manifest must be a JSON object.")
    expected_keys = {
        "schema_version",
        "classification",
        "evidence_class",
        "artifact",
        "bytes",
        "sha256",
        "formal_optimizer_steps",
        "synthetic_optimizer_steps",
    }
    if set(manifest) != expected_keys:
        raise ValueError("Unexpected checkpoint manifest schema.")
    if manifest["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError("Checkpoint manifest schema version mismatch.")
    if manifest["classification"] != MANIFEST_CLASSIFICATION:
        raise ValueError("Checkpoint manifest classification mismatch.")
    if manifest["evidence_class"] != "DERIVED":
        raise ValueError("Checkpoint manifest evidence class mismatch.")
    if manifest["artifact"] != target.name:
        raise ValueError("Checkpoint manifest artifact name mismatch.")
    if manifest["formal_optimizer_steps"] != 0:
        raise ValueError("Formal optimizer steps must be zero.")
    synthetic_steps = manifest["synthetic_optimizer_steps"]
    if (
        isinstance(synthetic_steps, bool)
        or not isinstance(synthetic_steps, int)
        or synthetic_steps <= 0
    ):
        raise ValueError("Manifest synthetic optimizer step count is invalid.")
    if isinstance(manifest["bytes"], bool) or not isinstance(manifest["bytes"], int):
        raise ValueError("Checkpoint manifest byte count is invalid.")
    if manifest["bytes"] != target.stat().st_size:
        raise ValueError("Checkpoint byte count does not match the manifest.")
    if not _HEX64.fullmatch(manifest["sha256"]):
        raise ValueError("Checkpoint manifest SHA256 is invalid.")
    if _sha256_file(target) != manifest["sha256"].upper():
        raise ValueError("Checkpoint SHA256 does not match the manifest.")
    return manifest


def load_phase3_checkpoint(
    *,
    checkpoint_path: Path,
    allowed_root: Path,
    model: DenseNetBC100Cifar10,
    optimizer: torch.optim.Optimizer,
    expected_master_seed: int,
    expected_provenance: CheckpointProvenance,
    expected_cuda_device_indices: tuple[int, ...] = (),
) -> CheckpointLoadResult:
    """Verify everything, then restore model/optimizer/RNG state exactly."""

    target, _ = _resolve_target(checkpoint_path, allowed_root)
    _require_existing_regular_file(target)
    manifest = _load_manifest(target)
    payload = torch.load(target, map_location="cpu", weights_only=True)
    expected_keys = {
        "schema_version",
        "classification",
        "synthetic_classification",
        "formal_optimizer_steps",
        "synthetic_optimizer_steps",
        "completed_epoch",
        "next_epoch",
        "master_seed",
        "policy_ids",
        "provenance",
        "parameter_names",
        "model_metadata",
        "model_state",
        "optimizer_state",
        "rng_state",
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise ValueError("Unexpected checkpoint payload schema.")
    if payload["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError("Checkpoint schema version mismatch.")
    if payload["classification"] != CHECKPOINT_CLASSIFICATION:
        raise ValueError("Checkpoint classification mismatch.")
    if payload["synthetic_classification"] != SYNTHETIC_CLASSIFICATION:
        raise ValueError("Checkpoint synthetic classification mismatch.")
    if payload["formal_optimizer_steps"] != 0:
        raise ValueError("Formal optimizer steps must be zero.")
    synthetic_steps = payload["synthetic_optimizer_steps"]
    if isinstance(synthetic_steps, bool) or not isinstance(synthetic_steps, int):
        raise ValueError("Synthetic optimizer step count is invalid.")
    if synthetic_steps <= 0 or synthetic_steps != manifest["synthetic_optimizer_steps"]:
        raise ValueError("Synthetic optimizer step count mismatch.")
    completed_epoch = payload["completed_epoch"]
    next_epoch = payload["next_epoch"]
    if (
        isinstance(completed_epoch, bool)
        or not isinstance(completed_epoch, int)
        or not 1 <= completed_epoch <= 300
        or next_epoch != completed_epoch + 1
    ):
        raise ValueError("Checkpoint epoch cursor is invalid.")
    seed = require_project_master_seed(expected_master_seed)
    if payload["master_seed"] != seed:
        raise ValueError("Checkpoint master seed mismatch.")
    if payload["policy_ids"] != _policy_ids():
        raise ValueError("Checkpoint policy identifiers mismatch.")
    if payload["provenance"] != asdict(expected_provenance):
        raise ValueError("Checkpoint provenance mismatch.")
    if payload["parameter_names"] != _parameter_names(model):
        raise ValueError("Checkpoint parameter names/order mismatch.")
    if payload["model_metadata"] != _model_metadata(model):
        raise ValueError("Checkpoint model metadata mismatch.")
    _validate_model_state(payload["model_state"], model)
    _validate_optimizer_state(
        payload["optimizer_state"], model, completed_epoch=completed_epoch
    )
    _validate_rng_state(payload["rng_state"], expected_cuda_device_indices)
    validate_phase3_optimizer(model, optimizer)

    # All fail-closed checks above precede state mutation.
    model.load_state_dict(payload["model_state"], strict=True)
    optimizer.load_state_dict(payload["optimizer_state"])
    validate_phase3_optimizer(model, optimizer)
    random.setstate(payload["rng_state"]["python"])
    torch.random.set_rng_state(payload["rng_state"]["torch_cpu"])
    for entry in payload["rng_state"]["torch_cuda"]:
        torch.cuda.set_rng_state(entry["state"], device=entry["device_index"])
    return CheckpointLoadResult(
        completed_epoch=completed_epoch,
        next_epoch=next_epoch,
        master_seed=seed,
        synthetic_optimizer_steps=synthetic_steps,
        formal_optimizer_steps=0,
        checkpoint_sha256=manifest["sha256"].upper(),
    )
