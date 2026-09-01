"""Run the human-approved closed Phase 4 exact-device diagnostic once.

Worker A performs 11 generated physical-batch-64 optimizer calls.  Fresh Worker
B loads the call-6 checkpoint and replays calls 7-11.  Only after exact replay
and OBSERVED-FIT does a third fresh worker consume the approved first 64 CIFAR
training decisions for one train-mode raw-logit forward under ``no_grad``.

The script never computes CIFAR loss/backward/optimizer/prediction/accuracy and
never performs a formal optimizer step.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any

import torch
from torch.utils.data import DataLoader

from densenet_reproduction import (
    CheckpointProvenance,
    Cifar10BinaryDataset,
    FixedAugmentedSampler,
    PHASE4_CHECKPOINT_CALL,
    PHASE4_CLASSIFICATION,
    PHASE4_EXPECTED_COMPUTE_CAPABILITY,
    PHASE4_EXPECTED_GPU_NAME,
    PHASE4_EXPECTED_GPU_UUID,
    PHASE4_MASTER_SEED,
    Phase4ScopeLedger,
    SyntheticStepLedger,
    build_phase3_optimizer,
    build_project_seeded_model,
    first_phase4_cifar_requests,
    initialize_runtime_rngs,
    load_phase3_checkpoint,
    loader_worker_base_seed,
    make_phase4_synthetic_batch,
    named_tensors_sha256,
    optimizer_state_sha256,
    phase4_synthetic_seed,
    prepare_cifar10_binary_archive,
    runtime_seed_bundle,
    save_phase3_checkpoint,
    state_dict_sha256,
    synthetic_mechanics_step,
    tensor_sha256,
    validate_success_report,
    verify_file_identity,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "docs" / "phase4_entry_decision_proposal.md"
ENVIRONMENT_LOCK_PATH = PROJECT_ROOT / "requirements" / "environment-lock.txt"
ARTIFACT_LOCK_PATH = PROJECT_ROOT / "evidence" / "cifar10-artifacts.json"
DEFAULT_BINARY_ARCHIVE = PROJECT_ROOT / "data" / "raw" / "cifar-10-binary.tar.gz"
DEFAULT_PREPARED = PROJECT_ROOT / "data" / "prepared" / "cifar-10-batches-bin"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _git_identity() -> dict[str, Any]:
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
    return {"source_commit": commit, "worktree_clean": status == ""}


def _provenance(source_commit: str) -> CheckpointProvenance:
    return CheckpointProvenance(
        source_commit=source_commit,
        environment_lock_sha256=_sha256_file(ENVIRONMENT_LOCK_PATH),
        dataset_sha256="C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD",
        config_sha256=_sha256_file(CONFIG_PATH),
    )


def _require_policy() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        raise RuntimeError("CUBLAS_WORKSPACE_CONFIG mismatch")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.conv.fp32_precision = "ieee"
    torch.backends.cuda.matmul.fp32_precision = "ieee"
    if torch.is_autocast_enabled("cuda"):
        raise RuntimeError("CUDA autocast must be disabled")


def _nvidia_snapshot() -> dict[str, str]:
    output = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,uuid,name,driver_version,driver_model.current",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip().splitlines()
    if len(output) != 1:
        raise RuntimeError("Exactly one GPU must be visible to Phase 4")
    fields = [field.strip() for field in output[0].split(",")]
    if len(fields) != 5 or fields[0] != "0":
        raise RuntimeError("Unexpected nvidia-smi identity row")
    return {
        "nvidia_smi_uuid": fields[1],
        "nvidia_smi_name": fields[2],
        "driver_version": fields[3],
        "driver_model": fields[4],
    }


def _runtime_snapshot(device: torch.device) -> dict[str, Any]:
    properties = torch.cuda.get_device_properties(device)
    uuid = f"GPU-{properties.uuid}"
    capability = list(torch.cuda.get_device_capability(device))
    nvidia = _nvidia_snapshot()
    if properties.name != PHASE4_EXPECTED_GPU_NAME:
        raise RuntimeError("GPU name mismatch")
    if uuid != PHASE4_EXPECTED_GPU_UUID:
        raise RuntimeError("GPU UUID mismatch")
    if tuple(capability) != PHASE4_EXPECTED_COMPUTE_CAPABILITY:
        raise RuntimeError("GPU compute capability mismatch")
    if nvidia["nvidia_smi_uuid"] != uuid or nvidia["nvidia_smi_name"] != properties.name:
        raise RuntimeError("PyTorch and nvidia-smi GPU identities differ")
    return {
        "python": sys.version,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "gpu_name": properties.name,
        "gpu_uuid": uuid,
        "compute_capability": capability,
        "gpu_total_memory_bytes": properties.total_memory,
        **nvidia,
        "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
        "cudnn_deterministic": torch.backends.cudnn.deterministic,
        "cudnn_convolution_fp32_precision": torch.backends.cudnn.conv.fp32_precision,
        "matmul_fp32_precision": torch.backends.cuda.matmul.fp32_precision,
        "amp_used": False,
        "compile_used": False,
        "recomputation_used": False,
        "gradient_accumulation_used": False,
    }


def _memory(device: torch.device) -> dict[str, int]:
    torch.cuda.synchronize(device)
    free, total = torch.cuda.mem_get_info(device)
    return {
        "allocated_bytes": torch.cuda.memory_allocated(device),
        "reserved_bytes": torch.cuda.memory_reserved(device),
        "free_bytes": free,
        "total_bytes": total,
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(device),
        "peak_reserved_bytes": torch.cuda.max_memory_reserved(device),
    }


def _rng_sha256(device: torch.device) -> str:
    items = [
        ("torch_cpu", torch.random.get_rng_state()),
        ("torch_cuda_0", torch.cuda.get_rng_state(device)),
    ]
    digest = hashlib.sha256()
    digest.update(repr(__import__("random").getstate()).encode("utf-8"))
    digest.update(named_tensors_sha256(items).encode("ascii"))
    return digest.hexdigest().upper()


def _loss_record(loss: torch.Tensor) -> dict[str, Any]:
    return {"value": float(loss.cpu()), "sha256": tensor_sha256(loss)}


def _finite_optimizer_state(optimizer: torch.optim.Optimizer) -> tuple[int, int]:
    tensors = 0
    nonfinite = 0
    for state in optimizer.state.values():
        for value in state.values():
            if isinstance(value, torch.Tensor):
                tensors += 1
                if not bool(torch.isfinite(value).all()):
                    nonfinite += 1
    return tensors, nonfinite


def _worker_a(checkpoint: Path, source_commit: str) -> dict[str, Any]:
    _require_policy()
    device = torch.device("cuda:0")
    runtime = _runtime_snapshot(device)
    memory: dict[str, dict[str, int]] = {"worker_a_before_model": _memory(device)}
    seed_bundle = runtime_seed_bundle(PHASE4_MASTER_SEED, cuda_device_indices=(0,))
    model = build_project_seeded_model(PHASE4_MASTER_SEED).to(device)
    initialize_runtime_rngs(seed_bundle)
    optimizer = build_phase3_optimizer(model, epoch=1)
    ledger = SyntheticStepLedger()
    memory["worker_a_after_model"] = _memory(device)
    timings: list[float] = []
    losses: dict[str, dict[str, Any]] = {}
    checkpoint_manifest: dict[str, Any] | None = None
    checkpoint_rng = ""
    gradient_count = 0

    for call_index in range(1, 12):
        batch = make_phase4_synthetic_batch(call_index, device=device)
        memory[f"worker_a_call_{call_index:02d}_batch"] = _memory(device)
        stages: dict[str, dict[str, int]] = {}

        def capture(stage: str) -> None:
            stages[stage] = _memory(device)

        if call_index == 1:
            loss = synthetic_mechanics_step(
                model=model,
                optimizer=optimizer,
                batch=batch,
                epoch=1,
                ledger=ledger,
                stage_callback=capture,
            )
            torch.cuda.synchronize(device)
            torch.cuda.reset_peak_memory_stats(device)
        else:
            torch.cuda.synchronize(device)
            started = time.perf_counter()
            loss = synthetic_mechanics_step(
                model=model,
                optimizer=optimizer,
                batch=batch,
                epoch=1,
                ledger=ledger,
                stage_callback=capture,
            )
            torch.cuda.synchronize(device)
            elapsed = time.perf_counter() - started
            if not math.isfinite(elapsed) or elapsed <= 0:
                raise RuntimeError("Invalid synchronized update duration")
            timings.append(elapsed)
        for stage, record in stages.items():
            memory[f"worker_a_call_{call_index:02d}_{stage}"] = record
        memory[f"worker_a_call_{call_index:02d}_complete"] = _memory(device)
        gradient_count = sum(parameter.grad is not None for parameter in model.parameters())
        if call_index >= 7:
            losses[str(call_index)] = _loss_record(loss)
        if call_index == PHASE4_CHECKPOINT_CALL:
            checkpoint_manifest = save_phase3_checkpoint(
                checkpoint_path=checkpoint,
                allowed_root=checkpoint.parent,
                model=model,
                optimizer=optimizer,
                ledger=ledger,
                completed_epoch=PHASE4_CHECKPOINT_CALL,
                master_seed=PHASE4_MASTER_SEED,
                provenance=_provenance(source_commit),
                cuda_device_indices=(0,),
            )
            checkpoint_rng = _rng_sha256(device)
            memory["worker_a_after_checkpoint_save"] = _memory(device)

    if checkpoint_manifest is None or len(timings) != 10:
        raise RuntimeError("Worker A did not complete the closed trajectory")
    optimizer_tensors, optimizer_nonfinite = _finite_optimizer_state(optimizer)
    bn_counters = [
        int(value.item())
        for name, value in model.state_dict().items()
        if name.endswith("num_batches_tracked")
    ]
    return {
        "ok": True,
        "actual_optimizer_calls": ledger.synthetic_optimizer_steps,
        "formal_optimizer_steps": ledger.formal_optimizer_steps,
        "runtime": runtime,
        "memory_records": memory,
        "measured_update_seconds": timings,
        "loss_suffix": losses,
        "checkpoint_sha256": checkpoint_manifest["sha256"],
        "checkpoint_rng_sha256": checkpoint_rng,
        "final_model_state_sha256": state_dict_sha256(model),
        "final_optimizer_state_sha256": optimizer_state_sha256(model, optimizer),
        "final_ledger": ledger.synthetic_optimizer_steps,
        "gradient_tensors": gradient_count,
        "optimizer_state_tensors": optimizer_tensors,
        "optimizer_nonfinite_tensors": optimizer_nonfinite,
        "bn_counter_count": len(bn_counters),
        "bn_counters_all_11": len(bn_counters) == 99 and set(bn_counters) == {11},
        "batch_seeds": {str(index): phase4_synthetic_seed(index) for index in range(1, 12)},
    }


def _worker_b(checkpoint: Path, source_commit: str) -> dict[str, Any]:
    _require_policy()
    device = torch.device("cuda:0")
    runtime = _runtime_snapshot(device)
    memory: dict[str, dict[str, int]] = {"worker_b_before_model": _memory(device)}
    model = build_project_seeded_model(PHASE4_MASTER_SEED).to(device)
    optimizer = build_phase3_optimizer(model, epoch=1)
    memory["worker_b_after_model"] = _memory(device)
    result = load_phase3_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=checkpoint.parent,
        model=model,
        optimizer=optimizer,
        expected_master_seed=PHASE4_MASTER_SEED,
        expected_provenance=_provenance(source_commit),
        expected_cuda_device_indices=(0,),
    )
    memory["worker_b_after_checkpoint_reload"] = _memory(device)
    checkpoint_rng = _rng_sha256(device)
    ledger = SyntheticStepLedger(result.synthetic_optimizer_steps)
    losses: dict[str, dict[str, Any]] = {}
    for call_index in range(7, 12):
        batch = make_phase4_synthetic_batch(call_index, device=device)
        loss = synthetic_mechanics_step(
            model=model,
            optimizer=optimizer,
            batch=batch,
            epoch=1,
            ledger=ledger,
        )
        losses[str(call_index)] = _loss_record(loss)
        memory[f"worker_b_call_{call_index:02d}_complete"] = _memory(device)
    torch.cuda.synchronize(device)
    return {
        "ok": True,
        "actual_optimizer_calls": 5,
        "formal_optimizer_steps": ledger.formal_optimizer_steps,
        "runtime": runtime,
        "memory_records": memory,
        "loss_suffix": losses,
        "checkpoint_sha256": result.checkpoint_sha256,
        "checkpoint_rng_sha256": checkpoint_rng,
        "final_model_state_sha256": state_dict_sha256(model),
        "final_optimizer_state_sha256": optimizer_state_sha256(model, optimizer),
        "final_ledger": ledger.synthetic_optimizer_steps,
    }


def _cifar_worker(
    binary_archive: Path, prepared: Path, source_commit: str
) -> dict[str, Any]:
    _require_policy()
    device = torch.device("cuda:0")
    runtime = _runtime_snapshot(device)
    lock = json.loads(ARTIFACT_LOCK_PATH.read_text(encoding="utf-8"))
    artifact = lock["artifacts"]["toronto_binary"]
    identity = verify_file_identity(
        binary_archive,
        expected_md5=artifact["md5"],
        expected_sha256=artifact["sha256"],
    )
    if identity["sha256"] != _provenance(source_commit).dataset_sha256:
        raise RuntimeError("Approved CIFAR archive SHA256 mismatch")
    verified_prepared = prepare_cifar10_binary_archive(
        binary_archive,
        prepared.parent,
        expected_md5=artifact["md5"],
        expected_sha256=artifact["sha256"],
    )
    if verified_prepared.resolve() != prepared.resolve():
        raise RuntimeError("Verified prepared CIFAR directory path mismatch")
    requests = first_phase4_cifar_requests()
    sampler = FixedAugmentedSampler(requests)
    request_digest = hashlib.sha256()
    for request in requests:
        request_digest.update(request.index.to_bytes(4, "big"))
        request_digest.update(bytes([int(request.decision.horizontal_flip)]))
        request_digest.update(bytes([request.decision.crop_x, request.decision.crop_y]))
    dataset = Cifar10BinaryDataset(prepared, split="train")
    loader = DataLoader(
        dataset,
        batch_size=64,
        sampler=sampler,
        num_workers=2,
        drop_last=False,
        pin_memory=False,
        generator=torch.Generator().manual_seed(
            loader_worker_base_seed(PHASE4_MASTER_SEED, 1)
        ),
        multiprocessing_context="spawn",
    )
    try:
        batches = iter(loader)
        images, targets = next(batches)
        try:
            next(batches)
        except StopIteration:
            pass
        else:
            raise RuntimeError("Bounded CIFAR loader emitted more than one batch")
    finally:
        dataset.close()
    if tuple(images.shape) != (64, 3, 32, 32) or images.dtype is not torch.float32:
        raise RuntimeError("Bounded CIFAR input contract mismatch")
    if tuple(targets.shape) != (64,) or targets.dtype is not torch.long:
        raise RuntimeError("Bounded CIFAR target contract mismatch")
    seed_bundle = runtime_seed_bundle(PHASE4_MASTER_SEED, cuda_device_indices=(0,))
    model = build_project_seeded_model(PHASE4_MASTER_SEED).to(device)
    initialize_runtime_rngs(seed_bundle)
    model.train()
    inputs = images.to(device, non_blocking=False)
    before_counters = {
        name: int(value.item())
        for name, value in model.state_dict().items()
        if name.endswith("num_batches_tracked")
    }
    with torch.no_grad():
        logits = model(inputs)
    torch.cuda.synchronize(device)
    after_counters = {
        name: int(value.item())
        for name, value in model.state_dict().items()
        if name.endswith("num_batches_tracked")
    }
    advanced = sum(after_counters[name] == before_counters[name] + 1 for name in before_counters)
    if tuple(logits.shape) != (64, 10) or logits.dtype is not torch.float32:
        raise RuntimeError("Raw-logit contract mismatch")
    if not bool(torch.isfinite(logits).all()):
        raise RuntimeError("Non-finite CIFAR raw logits")
    grads_none = all(parameter.grad is None for parameter in model.parameters())
    if advanced != 99 or not grads_none:
        raise RuntimeError("CIFAR forward-only state contract mismatch")
    return {
        "ok": True,
        "runtime": runtime,
        "artifact": identity,
        "samples": images.shape[0],
        "forward_calls": 1,
        "workers": 2,
        "batches": 1,
        "drop_last": False,
        "pin_memory": False,
        "non_blocking_transfer": False,
        "request_count": len(requests),
        "request_order_and_decisions_sha256": request_digest.hexdigest().upper(),
        "inputs_sha256": tensor_sha256(images),
        "targets_sha256": tensor_sha256(targets),
        "logits_sha256": tensor_sha256(logits),
        "logits_shape": list(logits.shape),
        "logits_finite": True,
        "model_state_sha256_after_forward": state_dict_sha256(model),
        "bn_counters_advanced": advanced,
        "all_parameter_grads_none_after_forward": grads_none,
        "cifar_loss_calls": 0,
        "cifar_backward_calls": 0,
        "cifar_optimizer_calls": 0,
        "predictions_or_argmax": 0,
        "accuracy_or_error_computations": 0,
        "validation_or_test_samples": 0,
    }


def _worker_entry(arguments: argparse.Namespace) -> None:
    try:
        if arguments.worker == "a":
            result = _worker_a(arguments.checkpoint, arguments.source_commit)
        elif arguments.worker == "b":
            result = _worker_b(arguments.checkpoint, arguments.source_commit)
        elif arguments.worker == "cifar":
            result = _cifar_worker(
                arguments.binary_archive, arguments.prepared, arguments.source_commit
            )
        else:
            raise ValueError("Unknown worker")
    except torch.cuda.OutOfMemoryError as error:
        result = {
            "ok": False,
            "error_type": "CUDA_OUT_OF_MEMORY",
            "error": str(error),
            "formal_optimizer_steps": 0,
        }
    except Exception as error:
        result = {
            "ok": False,
            "error_type": type(error).__name__,
            "error": str(error),
            "formal_optimizer_steps": 0,
        }
    print(json.dumps(result, sort_keys=True))


def _spawn(
    role: str,
    *,
    checkpoint: Path,
    source_commit: str,
    binary_archive: Path,
    prepared: Path,
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    environment["PYTHONHASHSEED"] = "0"
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            role,
            "--checkpoint",
            str(checkpoint),
            "--source-commit",
            source_commit,
            "--binary-archive",
            str(binary_archive),
            "--prepared",
            str(prepared),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    return json.loads(completed.stdout.decode("utf-8"))


def run_diagnostic(*, binary_archive: Path, prepared: Path) -> dict[str, Any]:
    git = _git_identity()
    if not git["worktree_clean"]:
        raise RuntimeError("Phase 4 source worktree must be clean before execution")
    source_commit = git["source_commit"]
    provenance = _provenance(source_commit)
    with tempfile.TemporaryDirectory(prefix="densenet-phase4-") as temporary:
        checkpoint = Path(temporary) / "call_006.pt"
        worker_a = _spawn(
            "a",
            checkpoint=checkpoint,
            source_commit=source_commit,
            binary_archive=binary_archive,
            prepared=prepared,
        )
        if not worker_a.get("ok"):
            disposition = (
                "OBSERVED-NOT-FIT"
                if worker_a.get("error_type") == "CUDA_OUT_OF_MEMORY"
                else "INVALID"
            )
            return {
                "classification": PHASE4_CLASSIFICATION,
                "evidence_class": "DERIVED",
                "record_date": date.today().isoformat(),
                "disposition": disposition,
                "worker_a": worker_a,
                "provenance": {
                    "source_commit": source_commit,
                    "environment_lock_sha256": provenance.environment_lock_sha256,
                    "dataset_sha256": provenance.dataset_sha256,
                    "phase4_config_sha256": provenance.config_sha256,
                },
                "scope": Phase4ScopeLedger().as_dict(),
            }
        worker_b = _spawn(
            "b",
            checkpoint=checkpoint,
            source_commit=source_commit,
            binary_archive=binary_archive,
            prepared=prepared,
        )
        if not worker_b.get("ok"):
            return {
                "classification": PHASE4_CLASSIFICATION,
                "evidence_class": "DERIVED",
                "record_date": date.today().isoformat(),
                "disposition": "INVALID",
                "worker_a": worker_a,
                "worker_b": worker_b,
                "provenance": {
                    "source_commit": source_commit,
                    "environment_lock_sha256": provenance.environment_lock_sha256,
                    "dataset_sha256": provenance.dataset_sha256,
                    "phase4_config_sha256": provenance.config_sha256,
                },
                "scope": Phase4ScopeLedger(
                    synthetic_optimizer_calls=worker_a["actual_optimizer_calls"]
                ).as_dict(),
            }
        replay = {
            "loss_suffix_bit_exact": worker_a["loss_suffix"] == worker_b["loss_suffix"],
            "model_state_bit_exact": worker_a["final_model_state_sha256"] == worker_b["final_model_state_sha256"],
            "optimizer_state_bit_exact": worker_a["final_optimizer_state_sha256"] == worker_b["final_optimizer_state_sha256"],
            "rng_state_at_checkpoint_bit_exact": worker_a["checkpoint_rng_sha256"] == worker_b["checkpoint_rng_sha256"],
            "step_ledger_bit_exact": worker_a["final_ledger"] == worker_b["final_ledger"] == 11,
            "checkpoint_identity_bit_exact": worker_a["checkpoint_sha256"] == worker_b["checkpoint_sha256"],
        }
        synthetic_fit = (
            all(replay.values())
            and worker_a["actual_optimizer_calls"] == 11
            and worker_b["actual_optimizer_calls"] == 5
            and worker_a["formal_optimizer_steps"] == worker_b["formal_optimizer_steps"] == 0
            and worker_a["gradient_tensors"] == 299
            and worker_a["optimizer_state_tensors"] == 299
            and worker_a["optimizer_nonfinite_tensors"] == 0
            and worker_a["bn_counters_all_11"] is True
        )
        if not synthetic_fit:
            return {
                "classification": PHASE4_CLASSIFICATION,
                "evidence_class": "DERIVED",
                "record_date": date.today().isoformat(),
                "disposition": "INVALID",
                "worker_a": worker_a,
                "worker_b": worker_b,
                "replay": replay,
                "provenance": {
                    "source_commit": source_commit,
                    "environment_lock_sha256": provenance.environment_lock_sha256,
                    "dataset_sha256": provenance.dataset_sha256,
                    "phase4_config_sha256": provenance.config_sha256,
                },
                "scope": Phase4ScopeLedger(synthetic_optimizer_calls=16).as_dict(),
            }
        cifar = _spawn(
            "cifar",
            checkpoint=checkpoint,
            source_commit=source_commit,
            binary_archive=binary_archive,
            prepared=prepared,
        )
        if not cifar.get("ok"):
            return {
                "classification": PHASE4_CLASSIFICATION,
                "evidence_class": "DERIVED",
                "record_date": date.today().isoformat(),
                "disposition": "INVALID",
                "worker_a": worker_a,
                "worker_b": worker_b,
                "cifar_forward": cifar,
                "replay": replay,
                "provenance": {
                    "source_commit": source_commit,
                    "environment_lock_sha256": provenance.environment_lock_sha256,
                    "dataset_sha256": provenance.dataset_sha256,
                    "phase4_config_sha256": provenance.config_sha256,
                },
                "scope": Phase4ScopeLedger(synthetic_optimizer_calls=16).as_dict(),
            }

    scope = Phase4ScopeLedger(
        synthetic_optimizer_calls=16,
        cifar_samples_read=64,
        cifar_forward_calls=1,
    )
    timings = worker_a["measured_update_seconds"]
    memory_records = {
        **worker_a["memory_records"],
        **worker_b["memory_records"],
    }
    final = {
        "classification": PHASE4_CLASSIFICATION,
        "evidence_class": "DERIVED",
        "record_date": date.today().isoformat(),
        "disposition": "OBSERVED-FIT",
        "provenance": {
            "source_commit": source_commit,
            "environment_lock_sha256": provenance.environment_lock_sha256,
            "dataset_sha256": provenance.dataset_sha256,
            "phase4_config_sha256": provenance.config_sha256,
        },
        "runtime": worker_a["runtime"],
        "memory_records": memory_records,
        "synthetic": {
            "physical_batch_size": 64,
            "worker_a_calls": worker_a["actual_optimizer_calls"],
            "worker_b_calls": worker_b["actual_optimizer_calls"],
            "total_calls": 16,
            "warmup_calls": 1,
            "measured_calls": 10,
            "measured_update_seconds": timings,
            "timing_includes_required_stage_memory_instrumentation": True,
            "timing_summary_seconds": {
                "arithmetic_mean": statistics.fmean(timings),
                "median": statistics.median(timings),
                "minimum": min(timings),
                "maximum": max(timings),
            },
            "paper_derived_updates": 234_600,
            "generated_kernel_projection_seconds_excluding_dataloader_evaluation_checkpoint_and_contention": statistics.fmean(timings) * 234_600,
            "gradient_tensors": worker_a["gradient_tensors"],
            "momentum_state_tensors": worker_a["optimizer_state_tensors"],
            "batch_seeds": worker_a["batch_seeds"],
            "final_model_state_sha256": worker_a["final_model_state_sha256"],
            "final_optimizer_state_sha256": worker_a["final_optimizer_state_sha256"],
            "checkpoint_sha256": worker_a["checkpoint_sha256"],
        },
        "replay": replay,
        "cifar_forward": {key: value for key, value in cifar.items() if key not in {"ok", "runtime"}},
        "scope": scope.as_dict(),
        "headroom_policy": "NO_AUTOMATIC_THRESHOLD_HUMAN_COMPLETION_DECISION_REQUIRED",
        "formal_reproduction_result": False,
    }
    validate_success_report(
        final,
        expected_source_commit=source_commit,
        expected_environment_lock_sha256=provenance.environment_lock_sha256,
        expected_config_sha256=provenance.config_sha256,
    )
    return final


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=("a", "b", "cifar"))
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--binary-archive", type=Path, default=DEFAULT_BINARY_ARCHIVE)
    parser.add_argument("--prepared", type=Path, default=DEFAULT_PREPARED)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.worker:
        if arguments.checkpoint is None or arguments.source_commit is None:
            parser.error("worker mode requires checkpoint and source commit")
        _worker_entry(arguments)
        return
    report = run_diagnostic(
        binary_archive=arguments.binary_archive,
        prepared=arguments.prepared,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output is not None:
        arguments.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
