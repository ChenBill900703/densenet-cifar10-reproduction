from __future__ import annotations

from copy import deepcopy
import hashlib
from itertools import islice

import pytest
import torch

from densenet_reproduction import (
    CandidateCifar10EpochSampler,
    FixedAugmentedSampler,
    PHASE4_CLASSIFICATION,
    PHASE4_EXPECTED_GPU_NAME,
    PHASE4_EXPECTED_GPU_UUID,
    PHASE4_MASTER_SEED,
    PHASE4_SYNTHETIC_BATCH_DOMAIN,
    Phase4ScopeLedger,
    first_phase4_cifar_requests,
    make_phase4_synthetic_batch,
    phase4_synthetic_seed,
    validate_memory_record,
    validate_success_report,
)


def _memory() -> dict[str, int]:
    return {
        "allocated_bytes": 100,
        "reserved_bytes": 200,
        "free_bytes": 800,
        "total_bytes": 1000,
        "peak_allocated_bytes": 150,
        "peak_reserved_bytes": 250,
    }


def _success_report() -> dict[str, object]:
    return {
        "classification": PHASE4_CLASSIFICATION,
        "evidence_class": "DERIVED",
        "disposition": "OBSERVED-FIT",
        "provenance": {
            "source_commit": "a" * 40,
            "environment_lock_sha256": "B" * 64,
            "dataset_sha256": "C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD",
            "phase4_config_sha256": "C" * 64,
        },
        "runtime": {
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
        },
        "synthetic": {
            "physical_batch_size": 64,
            "worker_a_calls": 11,
            "worker_b_calls": 5,
            "total_calls": 16,
            "warmup_calls": 1,
            "measured_calls": 10,
            "gradient_tensors": 299,
            "momentum_state_tensors": 299,
            "measured_update_seconds": [0.1] * 10,
        },
        "memory_records": {"stage": _memory()},
        "scope": Phase4ScopeLedger(
            synthetic_optimizer_calls=16,
            cifar_samples_read=64,
            cifar_forward_calls=1,
        ).as_dict(),
        "replay": {
            "loss_suffix_bit_exact": True,
            "model_state_bit_exact": True,
            "optimizer_state_bit_exact": True,
            "rng_state_at_checkpoint_bit_exact": True,
            "step_ledger_bit_exact": True,
            "checkpoint_identity_bit_exact": True,
        },
        "cifar_forward": {
            "samples": 64,
            "forward_calls": 1,
            "logits_shape": [64, 10],
            "bn_counters_advanced": 99,
            "all_parameter_grads_none_after_forward": True,
        },
    }


def test_phase4_seed_mapping_is_independent_sha256_domain() -> None:
    expected = int.from_bytes(
        hashlib.sha256(
            f"{PHASE4_SYNTHETIC_BATCH_DOMAIN}|{PHASE4_MASTER_SEED}|1".encode("ascii")
        ).digest()[:8],
        "big",
    ) & ((1 << 63) - 1)
    assert phase4_synthetic_seed(1) == expected
    assert len({phase4_synthetic_seed(index) for index in range(1, 12)}) == 11
    with pytest.raises(ValueError, match=r"\[1, 11\]"):
        phase4_synthetic_seed(0)
    with pytest.raises(ValueError, match=r"\[1, 11\]"):
        phase4_synthetic_seed(12)
    with pytest.raises(TypeError, match="integer"):
        phase4_synthetic_seed(True)


def test_phase4_factory_proves_one_physical_batch_without_accumulation() -> None:
    batch = make_phase4_synthetic_batch(1, device="cpu")
    assert batch.inputs.shape == (64, 3, 32, 32)
    assert batch.inputs.dtype is torch.float32
    assert batch.targets.shape == (64,)
    assert batch.targets.dtype is torch.long
    assert batch.generation_seed == phase4_synthetic_seed(1)


def test_bounded_sampler_is_exactly_first_64_full_epoch_decisions() -> None:
    expected = tuple(
        islice(
            CandidateCifar10EpochSampler(
                size=50_000, master_seed=PHASE4_MASTER_SEED, epoch=1
            ),
            64,
        )
    )
    requests = first_phase4_cifar_requests()
    assert requests == expected
    assert len(requests) == len({request.index for request in requests}) == 64
    assert tuple(FixedAugmentedSampler(requests)) == requests
    with pytest.raises(ValueError, match="first 64"):
        FixedAugmentedSampler(requests[1:] + requests[:1])


def test_scope_ledger_rejects_every_under_or_over_scope_success_claim() -> None:
    exact = Phase4ScopeLedger(
        synthetic_optimizer_calls=16,
        cifar_samples_read=64,
        cifar_forward_calls=1,
    )
    exact.require_final_success_scope()
    for field in exact.as_dict():
        mutation = exact.as_dict()
        mutation[field] += 1
        with pytest.raises(ValueError, match="scope ledger"):
            Phase4ScopeLedger(**mutation).require_final_success_scope()


@pytest.mark.parametrize(
    ("path", "replacement", "message"),
    [
        (("runtime", "gpu_uuid"), "GPU-wrong", "gpu_uuid"),
        (("runtime", "amp_used"), True, "amp_used"),
        (("runtime", "compile_used"), True, "compile_used"),
        (("runtime", "cudnn_convolution_fp32_precision"), "tf32", "precision"),
        (("synthetic", "measured_update_seconds"), [0.1] * 9, "ten"),
        (("synthetic", "measured_update_seconds"), [0.1] * 9 + [float("nan")], "finite"),
        (("replay", "model_state_bit_exact"), False, "model_state"),
        (("cifar_forward", "samples"), 65, "scope"),
        (("cifar_forward", "all_parameter_grads_none_after_forward"), False, "gradients"),
    ],
)
def test_success_report_fails_closed_on_policy_scope_and_replay_mutations(
    path: tuple[str, str], replacement: object, message: str
) -> None:
    report = _success_report()
    report[path[0]][path[1]] = replacement  # type: ignore[index]
    with pytest.raises(ValueError, match=message):
        validate_success_report(report)


def test_success_report_fails_closed_on_source_environment_config_and_dataset() -> None:
    report = _success_report()
    validate_success_report(
        report,
        expected_source_commit="a" * 40,
        expected_environment_lock_sha256="B" * 64,
        expected_config_sha256="C" * 64,
    )
    for keyword, wrong in (
        ("expected_source_commit", "d" * 40),
        ("expected_environment_lock_sha256", "D" * 64),
        ("expected_config_sha256", "D" * 64),
        ("expected_dataset_sha256", "D" * 64),
    ):
        with pytest.raises(ValueError, match="mismatch|Dataset"):
            validate_success_report(report, **{keyword: wrong})


def test_memory_record_requires_all_integer_byte_fields_and_consistency() -> None:
    validate_memory_record(_memory())
    missing = _memory()
    del missing["free_bytes"]
    with pytest.raises(ValueError, match="fields"):
        validate_memory_record(missing)
    wrong_type = _memory()
    wrong_type["free_bytes"] = 1.5  # type: ignore[assignment]
    with pytest.raises(TypeError, match="integer"):
        validate_memory_record(wrong_type)
    impossible = _memory()
    impossible["allocated_bytes"] = 201
    with pytest.raises(ValueError, match="Allocated"):
        validate_memory_record(impossible)


def test_success_report_rejects_missing_memory_field() -> None:
    report = deepcopy(_success_report())
    del report["memory_records"]["stage"]["free_bytes"]  # type: ignore[index]
    with pytest.raises(ValueError, match="fields"):
        validate_success_report(report)
