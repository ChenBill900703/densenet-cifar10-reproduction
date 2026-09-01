"""Closed Phase 4 exact-device diagnostic policy and pure audit helpers.

This module does not run the diagnostic on import.  Its only optimizer-capable
factory still returns generated tensors through the Phase 3 authorization
boundary.  CIFAR is never accepted by an optimizer API.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import islice
import json
import math
import re
from typing import Any, Final, Iterator, Sequence

import torch
from torch import Tensor

from .data import AugmentedIndex, CandidateCifar10EpochSampler
from .mechanics import (
    PROJECT_REPRODUCTION_SEEDS,
    SyntheticMechanicsBatch,
    derive_domain_seed,
    make_synthetic_mechanics_batch,
)


PHASE4_SYNTHETIC_BATCH_DOMAIN: Final[str] = "densenet-phase4-synthetic-batch-v1"
PHASE4_CLASSIFICATION: Final[str] = "PHASE4-EXACT-DEVICE-DIAGNOSTIC-NOT-FORMAL-RUN"
PHASE4_EXPECTED_GPU_NAME: Final[str] = "NVIDIA GeForce RTX 3070 Ti"
PHASE4_EXPECTED_GPU_UUID: Final[str] = (
    "GPU-9f68fb0f-9bd0-a95c-d16e-8362b9d59e2e"
)
PHASE4_EXPECTED_COMPUTE_CAPABILITY: Final[tuple[int, int]] = (8, 6)
PHASE4_MASTER_SEED: Final[int] = PROJECT_REPRODUCTION_SEEDS[0]
PHASE4_EPOCH: Final[int] = 1
PHASE4_BATCH_SIZE: Final[int] = 64
PHASE4_WORKER_A_CALLS: Final[int] = 11
PHASE4_WORKER_B_CALLS: Final[int] = 5
PHASE4_TOTAL_SYNTHETIC_CALLS: Final[int] = 16
PHASE4_MEASURED_CALLS: Final[int] = 10
PHASE4_CHECKPOINT_CALL: Final[int] = 6
PHASE4_CIFAR_SAMPLES: Final[int] = 64

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9A-F]{64}$")


@dataclass(slots=True)
class Phase4ScopeLedger:
    """Fail-closed counters separating every permitted and prohibited action."""

    synthetic_optimizer_calls: int = 0
    cifar_samples_read: int = 0
    cifar_forward_calls: int = 0
    cifar_loss_calls: int = 0
    cifar_backward_calls: int = 0
    cifar_optimizer_calls: int = 0
    predictions_or_argmax: int = 0
    accuracy_or_error_computations: int = 0
    validation_or_test_samples: int = 0
    pretrained_downloads: int = 0
    formal_optimizer_steps: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            name: int(getattr(self, name))
            for name in self.__dataclass_fields__
        }

    def require_final_success_scope(self) -> None:
        expected = {
            "synthetic_optimizer_calls": PHASE4_TOTAL_SYNTHETIC_CALLS,
            "cifar_samples_read": PHASE4_CIFAR_SAMPLES,
            "cifar_forward_calls": 1,
            "cifar_loss_calls": 0,
            "cifar_backward_calls": 0,
            "cifar_optimizer_calls": 0,
            "predictions_or_argmax": 0,
            "accuracy_or_error_computations": 0,
            "validation_or_test_samples": 0,
            "pretrained_downloads": 0,
            "formal_optimizer_steps": 0,
        }
        if self.as_dict() != expected:
            raise ValueError("Phase 4 scope ledger does not match the approved boundary.")


def phase4_synthetic_seed(call_index: int) -> int:
    """Return the approved domain-separated generated-batch seed for call 1..11."""

    if isinstance(call_index, bool) or not isinstance(call_index, int):
        raise TypeError("call_index must be an integer.")
    if not 1 <= call_index <= PHASE4_WORKER_A_CALLS:
        raise ValueError("call_index must be in [1, 11].")
    return derive_domain_seed(
        PHASE4_SYNTHETIC_BATCH_DOMAIN,
        PHASE4_MASTER_SEED,
        call_index,
    )


def make_phase4_synthetic_batch(
    call_index: int, *, device: torch.device | str
) -> SyntheticMechanicsBatch:
    """Create exactly one authorized physical batch-64 generated batch."""

    batch = make_synthetic_mechanics_batch(
        batch_size=PHASE4_BATCH_SIZE,
        generation_seed=phase4_synthetic_seed(call_index),
        device=device,
    )
    if tuple(batch.inputs.shape) != (64, 3, 32, 32):
        raise ValueError("Phase 4 requires one physical [64,3,32,32] batch.")
    if tuple(batch.targets.shape) != (64,):
        raise ValueError("Phase 4 requires 64 generated targets.")
    return batch


def first_phase4_cifar_requests() -> tuple[AugmentedIndex, ...]:
    """Materialize exactly the first 64 decisions of the full approved epoch."""

    sampler = CandidateCifar10EpochSampler(
        size=50_000,
        master_seed=PHASE4_MASTER_SEED,
        epoch=PHASE4_EPOCH,
    )
    requests = tuple(islice(sampler, PHASE4_CIFAR_SAMPLES))
    if len(requests) != PHASE4_CIFAR_SAMPLES:
        raise RuntimeError("Could not materialize the bounded CIFAR request set.")
    indices = [request.index for request in requests]
    if len(set(indices)) != PHASE4_CIFAR_SAMPLES:
        raise RuntimeError("Bounded CIFAR request set contains duplicate samples.")
    return requests


class FixedAugmentedSampler(Sequence[AugmentedIndex]):
    """Finite sampler whose length prevents DataLoader prefetch beyond 64 keys."""

    def __init__(self, requests: Sequence[AugmentedIndex]) -> None:
        self._requests = tuple(requests)
        if self._requests != first_phase4_cifar_requests():
            raise ValueError("Sampler requests are not the approved first 64 decisions.")

    def __getitem__(self, index: int) -> AugmentedIndex:
        return self._requests[index]

    def __len__(self) -> int:
        return len(self._requests)

    def __iter__(self) -> Iterator[AugmentedIndex]:
        return iter(self._requests)


def tensor_sha256(tensor: Tensor) -> str:
    """Hash tensor dtype, shape and canonical contiguous CPU bytes."""

    value = tensor.detach().cpu().contiguous()
    digest = hashlib.sha256()
    metadata = json.dumps(
        {"dtype": str(value.dtype), "shape": list(value.shape)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    digest.update(metadata)
    digest.update(bytes(value.reshape(-1).view(torch.uint8).tolist()))
    return digest.hexdigest().upper()


def named_tensors_sha256(items: Sequence[tuple[str, Tensor]]) -> str:
    """Hash an ordered named-tensor collection without NumPy."""

    digest = hashlib.sha256()
    for name, tensor in items:
        value = tensor.detach().cpu().contiguous()
        metadata = json.dumps(
            {"name": name, "dtype": str(value.dtype), "shape": list(value.shape)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest.update(len(metadata).to_bytes(8, "little"))
        digest.update(metadata)
        digest.update(bytes(value.reshape(-1).view(torch.uint8).tolist()))
    return digest.hexdigest().upper()


def optimizer_state_sha256(
    model: torch.nn.Module, optimizer: torch.optim.Optimizer
) -> str:
    """Hash the approved one-group optimizer state by stable parameter name."""

    parameter_names = {
        id(parameter): name for name, parameter in model.named_parameters()
    }
    group = optimizer.param_groups
    if len(group) != 1:
        raise ValueError("Phase 4 optimizer must have one parameter group.")
    digest = hashlib.sha256()
    settings = {
        key: value
        for key, value in group[0].items()
        if key != "params"
    }
    digest.update(
        json.dumps(settings, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    for parameter in group[0]["params"]:
        name = parameter_names.get(id(parameter))
        if name is None:
            raise ValueError("Optimizer contains a parameter outside the model.")
        state = optimizer.state.get(parameter, {})
        digest.update(name.encode("utf-8"))
        for key in sorted(state):
            digest.update(key.encode("utf-8"))
            value = state[key]
            if not isinstance(value, Tensor):
                digest.update(repr(value).encode("ascii"))
            else:
                digest.update(tensor_sha256(value).encode("ascii"))
    return digest.hexdigest().upper()


def validate_memory_record(record: dict[str, Any]) -> None:
    required = {
        "allocated_bytes",
        "reserved_bytes",
        "free_bytes",
        "total_bytes",
        "peak_allocated_bytes",
        "peak_reserved_bytes",
    }
    if set(record) != required:
        raise ValueError("Memory record fields do not match M-005.")
    if any(isinstance(record[name], bool) or not isinstance(record[name], int) for name in required):
        raise TypeError("Every memory measurement must be an integer byte count.")
    if any(record[name] < 0 for name in required):
        raise ValueError("Memory measurements must be non-negative.")
    if record["allocated_bytes"] > record["reserved_bytes"]:
        raise ValueError("Allocated bytes cannot exceed reserved bytes.")
    if record["free_bytes"] > record["total_bytes"]:
        raise ValueError("Free bytes cannot exceed total bytes.")
    if record["peak_allocated_bytes"] < record["allocated_bytes"]:
        raise ValueError("Peak allocated bytes cannot be below current allocated bytes.")
    if record["peak_reserved_bytes"] < record["reserved_bytes"]:
        raise ValueError("Peak reserved bytes cannot be below current reserved bytes.")


def validate_success_report(
    report: dict[str, Any],
    *,
    expected_source_commit: str | None = None,
    expected_environment_lock_sha256: str | None = None,
    expected_config_sha256: str | None = None,
    expected_dataset_sha256: str = "C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD",
) -> None:
    """Fail closed on a purported successful Phase 4 machine report."""

    if report.get("classification") != PHASE4_CLASSIFICATION:
        raise ValueError("Wrong Phase 4 report classification.")
    if report.get("evidence_class") != "DERIVED":
        raise ValueError("Wrong Phase 4 evidence class.")
    if report.get("disposition") != "OBSERVED-FIT":
        raise ValueError("Success report must be OBSERVED-FIT.")
    provenance = report.get("provenance", {})
    if not _HEX40.fullmatch(str(provenance.get("source_commit", ""))):
        raise ValueError("Source commit is not a full lowercase Git hash.")
    for name in ("environment_lock_sha256", "phase4_config_sha256"):
        if not _HEX64.fullmatch(str(provenance.get(name, ""))):
            raise ValueError(f"Invalid provenance hash: {name}.")
    if provenance.get("dataset_sha256") != expected_dataset_sha256:
        raise ValueError("Dataset SHA256 does not match the sole approved artifact.")
    expected_values = {
        "source_commit": expected_source_commit,
        "environment_lock_sha256": expected_environment_lock_sha256,
        "phase4_config_sha256": expected_config_sha256,
    }
    for name, expected in expected_values.items():
        if expected is not None and provenance.get(name) != expected:
            raise ValueError(f"Provenance mismatch: {name}.")
    runtime = report.get("runtime", {})
    exact_runtime = {
        "gpu_name": PHASE4_EXPECTED_GPU_NAME,
        "gpu_uuid": PHASE4_EXPECTED_GPU_UUID,
        "compute_capability": [8, 6],
        "cublas_workspace_config": ":4096:8",
        "deterministic_algorithms": True,
        "cudnn_benchmark": False,
        "cudnn_deterministic": True,
        "cudnn_convolution_fp32_precision": "ieee",
        "matmul_fp32_precision": "ieee",
        "amp_used": False,
        "compile_used": False,
        "recomputation_used": False,
        "gradient_accumulation_used": False,
    }
    for name, expected in exact_runtime.items():
        if runtime.get(name) != expected:
            raise ValueError(f"Runtime policy mismatch: {name}.")
    timing = report.get("synthetic", {}).get("measured_update_seconds", [])
    if len(timing) != PHASE4_MEASURED_CALLS:
        raise ValueError("Exactly ten measured update timings are required.")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
        for value in timing
    ):
        raise ValueError("Every measured duration must be finite and positive.")
    memory_records = report.get("memory_records", {})
    if not memory_records:
        raise ValueError("M-005 memory records are missing.")
    for record in memory_records.values():
        validate_memory_record(record)
    scope = Phase4ScopeLedger(**report.get("scope", {}))
    scope.require_final_success_scope()
    replay = report.get("replay", {})
    for name in (
        "loss_suffix_bit_exact",
        "model_state_bit_exact",
        "optimizer_state_bit_exact",
        "rng_state_at_checkpoint_bit_exact",
        "step_ledger_bit_exact",
        "checkpoint_identity_bit_exact",
    ):
        if replay.get(name) is not True:
            raise ValueError(f"Replay check failed: {name}.")
    cifar = report.get("cifar_forward", {})
    if cifar.get("samples") != 64 or cifar.get("forward_calls") != 1:
        raise ValueError("Bounded CIFAR forward scope is wrong.")
    if cifar.get("logits_shape") != [64, 10] or cifar.get("bn_counters_advanced") != 99:
        raise ValueError("CIFAR raw-logit/BatchNorm contract failed.")
    if cifar.get("all_parameter_grads_none_after_forward") is not True:
        raise ValueError("CIFAR forward unexpectedly created parameter gradients.")
    synthetic = report.get("synthetic", {})
    exact_synthetic = {
        "physical_batch_size": 64,
        "worker_a_calls": 11,
        "worker_b_calls": 5,
        "total_calls": 16,
        "warmup_calls": 1,
        "measured_calls": 10,
        "gradient_tensors": 299,
        "momentum_state_tensors": 299,
    }
    for name, expected in exact_synthetic.items():
        if synthetic.get(name) != expected:
            raise ValueError(f"Synthetic protocol mismatch: {name}.")
