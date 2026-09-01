"""Later Phase 6 formal training adapter, frozen and unexecuted in Phase 5."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
import math
import os
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader

from .data import (
    CandidateCifar10EpochSampler,
    Cifar10BinaryDataset,
    verify_prepared_cifar10_split,
)
from .formal_checkpoint import (
    FormalCheckpointProvenance,
    load_formal_checkpoint,
    read_formal_checkpoint_manifest,
    save_formal_checkpoint,
)
from .formal_runtime import FormalStepCoordinates, execute_accounted_optimizer_call
from .mechanics import (
    build_phase3_optimizer,
    build_project_seeded_model,
    initialize_runtime_rngs,
    loader_worker_base_seed,
    mean_cross_entropy,
    runtime_seed_bundle,
    set_epoch_learning_rate,
)
from .phase5 import (
    AppendOnlyAttemptLedger,
    LaunchIdentity,
    Phase6Authorization,
    validate_launch_identity,
    canonical_json_bytes,
)


@dataclass(frozen=True, slots=True)
class FormalTrainingRequest:
    prepared_directory: Path
    run_directory: Path
    master_seed: int
    device_index: int
    authorization: Phase6Authorization
    expected_launch: LaunchIdentity
    observed_launch: LaunchIdentity
    base_provenance: FormalCheckpointProvenance
    resume_checkpoint: Path | None = None
    resume_initial_boundary: bool = False


def enforce_formal_runtime_policy(device_index: int) -> torch.device:
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        raise RuntimeError("CUBLAS_WORKSPACE_CONFIG must already equal :4096:8.")
    if not torch.cuda.is_available() or device_index < 0 or device_index >= torch.cuda.device_count():
        raise RuntimeError("The frozen CUDA device is unavailable.")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.conv.fp32_precision = "ieee"
    torch.backends.cuda.matmul.fp32_precision = "ieee"
    if (
        not torch.are_deterministic_algorithms_enabled()
        or torch.backends.cudnn.benchmark
        or not torch.backends.cudnn.deterministic
        or torch.backends.cudnn.conv.fp32_precision != "ieee"
        or torch.backends.cuda.matmul.fp32_precision != "ieee"
    ):
        raise RuntimeError("Could not enforce the frozen deterministic FP32 policy.")
    return torch.device(f"cuda:{device_index}")


def _training_loader(
    dataset: Cifar10BinaryDataset, *, master_seed: int, epoch: int
) -> DataLoader[Any]:
    return DataLoader(
        dataset,
        batch_size=64,
        sampler=CandidateCifar10EpochSampler(
            size=50_000, master_seed=master_seed, epoch=epoch
        ),
        num_workers=2,
        drop_last=False,
        pin_memory=False,
        generator=torch.Generator().manual_seed(
            loader_worker_base_seed(master_seed, epoch)
        ),
        multiprocessing_context="spawn",
        persistent_workers=False,
    )


def _require_all_finite(
    model: torch.nn.Module, optimizer: torch.optim.Optimizer
) -> None:
    for name, parameter in model.named_parameters():
        if parameter.grad is None:
            raise RuntimeError(f"Missing gradient for {name}.")
        if not bool(torch.isfinite(parameter.grad).all()):
            raise FloatingPointError(f"Non-finite gradient for {name}.")
    for name, value in model.state_dict().items():
        if not bool(torch.isfinite(value).all()):
            raise FloatingPointError(f"Non-finite model state: {name}.")
    for state in optimizer.state.values():
        for value in state.values():
            if isinstance(value, torch.Tensor) and not bool(torch.isfinite(value).all()):
                raise FloatingPointError("Non-finite optimizer state.")


def _append_training_progress(path: Path, document: dict[str, Any]) -> None:
    with path.open("ab", buffering=0) as stream:
        stream.write(canonical_json_bytes(document))
        os.fsync(stream.fileno())


def _validate_training_progress(
    path: Path, *, master_seed: int, ledger: AppendOnlyAttemptLedger
) -> None:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Resume requires the existing append-only training log.")
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError("Training progress has a torn final record.")
    completion_counts: dict[str, int] = {}
    completed_calls = 0
    for ledger_record in ledger.records:
        if ledger_record["event"] == "completion":
            completed_calls += 1
            completion_counts[ledger_record["record_sha256"]] = completed_calls
    previous_physical_calls = 0
    for line in raw.splitlines():
        try:
            document = json.loads(line.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Training progress is not canonical JSONL.") from error
        if line + b"\n" != canonical_json_bytes(document):
            raise ValueError("Training progress contains a noncanonical record.")
        if set(document) != {
            "accepted_step",
            "batch_index",
            "classification",
            "epoch",
            "ledger_head_sha256",
            "loss_fp32_decimal",
            "master_seed",
            "physical_completed_calls",
        }:
            raise ValueError("Unexpected training-progress record schema.")
        epoch = document["epoch"]
        batch_index = document["batch_index"]
        accepted_step = document["accepted_step"]
        calls = document["physical_completed_calls"]
        if (
            document["classification"] != "FORMAL-TRAINING-PROGRESS-V1"
            or document["master_seed"] != master_seed
            or not isinstance(epoch, int)
            or isinstance(epoch, bool)
            or not 1 <= epoch <= 300
            or not isinstance(batch_index, int)
            or isinstance(batch_index, bool)
            or not 0 <= batch_index < 782
            or accepted_step != (epoch - 1) * 782 + batch_index + 1
            or not isinstance(calls, int)
            or isinstance(calls, bool)
            or calls <= previous_physical_calls
            or completion_counts.get(document["ledger_head_sha256"]) != calls
        ):
            raise ValueError("Training-progress record is inconsistent.")
        try:
            loss_value = float(document["loss_fp32_decimal"])
        except (TypeError, ValueError) as error:
            raise ValueError("Training-progress loss is invalid.") from error
        if not math.isfinite(loss_value):
            raise ValueError("Training-progress loss is non-finite.")
        previous_physical_calls = calls
    if previous_physical_calls > ledger.summary().completed_calls:
        raise ValueError("Training progress is ahead of the attempt ledger.")


def _require_initial_boundary_resume_state(
    run_root: Path, *, master_seed: int, ledger: AppendOnlyAttemptLedger
) -> None:
    if any("epoch-" in candidate.name for candidate in run_root.iterdir()):
        raise RuntimeError(
            "Initial-boundary resume is forbidden after any checkpoint artifact exists."
        )
    if any(record["master_seed"] != master_seed for record in ledger.records):
        raise ValueError("Initial-boundary attempt ledger contains another seed.")
    if ledger.summary().unresolved_intents:
        raise RuntimeError("Unresolved optimizer intent requires a new human decision.")


def _resume_provenance(
    request: FormalTrainingRequest,
) -> FormalCheckpointProvenance:
    if request.resume_checkpoint is None:
        return request.base_provenance
    manifest = read_formal_checkpoint_manifest(request.resume_checkpoint)
    observed = FormalCheckpointProvenance(**manifest["provenance"])
    expected = asdict(request.base_provenance)
    actual = asdict(observed)
    for key in expected:
        if key != "ledger_head_sha256" and expected[key] != actual[key]:
            raise ValueError(f"Resume checkpoint provenance mismatch: {key}")
    return observed


def run_formal_training_seed(request: FormalTrainingRequest) -> tuple[Path, ...]:
    """Execute one seed only after later approvals and exact launch validation.

    This function must not be called during Phase 5. Its presence lets the
    reviewed wheel be frozen before formal execution begins.
    """

    validate_launch_identity(request.expected_launch, request.observed_launch)
    from .phase5 import require_phase6_authorization

    require_phase6_authorization(
        request.authorization,
        expected_freeze_manifest_sha256=request.expected_launch.freeze_manifest_sha256,
    )
    if request.base_provenance.freeze_manifest_sha256 != request.expected_launch.freeze_manifest_sha256:
        raise ValueError("Checkpoint provenance and launch manifest differ.")
    prepared_verification = verify_prepared_cifar10_split(
        request.prepared_directory,
        split="train",
        expected_archive_sha256=request.expected_launch.dataset_sha256,
    )
    if request.resume_checkpoint is not None and request.resume_initial_boundary:
        raise ValueError("Checkpoint resume and initial-boundary resume are exclusive.")
    run_root = request.run_directory.resolve(strict=True)
    if not run_root.is_dir() or request.run_directory.is_symlink():
        raise ValueError("run_directory must be a regular precreated seed directory.")
    from .formal_runtime import require_formal_seed_training_order

    formal_root = run_root.parent.parent
    ordered_root = require_formal_seed_training_order(
        formal_root,
        request.expected_launch.freeze_manifest_sha256,
        request.master_seed,
        resuming=True,
    )
    if ordered_root != run_root:
        raise ValueError("run_directory differs from the frozen seed-order path.")
    ledger_path = run_root / "optimizer-attempts.jsonl"
    creating = request.resume_checkpoint is None and not request.resume_initial_boundary
    if creating and ledger_path.exists():
        raise FileExistsError("New formal run already has an attempt ledger.")
    if not creating and not ledger_path.is_file():
        raise RuntimeError("Formal resume requires the existing attempt ledger.")
    ledger = AppendOnlyAttemptLedger(ledger_path, create=creating)
    progress_path = run_root / "training-progress.jsonl"
    if creating:
        descriptor = os.open(
            progress_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
        )
        os.close(descriptor)
    else:
        _validate_training_progress(
            progress_path, master_seed=request.master_seed, ledger=ledger
        )
    if request.resume_initial_boundary:
        _require_initial_boundary_resume_state(
            run_root, master_seed=request.master_seed, ledger=ledger
        )
    if ledger.summary().unresolved_intents:
        raise RuntimeError("Unresolved optimizer intent requires a new human decision.")
    device = enforce_formal_runtime_policy(request.device_index)
    model = build_project_seeded_model(request.master_seed).to(device)
    optimizer = build_phase3_optimizer(model, epoch=1)
    initialize_runtime_rngs(
        runtime_seed_bundle(
            request.master_seed, cuda_device_indices=(request.device_index,)
        )
    )
    next_epoch = 1
    if request.resume_checkpoint is not None:
        result = load_formal_checkpoint(
            checkpoint_path=request.resume_checkpoint,
            allowed_root=run_root,
            model=model,
            optimizer=optimizer,
            expected_master_seed=request.master_seed,
            expected_provenance=_resume_provenance(request),
            expected_cuda_device_indices=(request.device_index,),
        )
        next_epoch = result.next_epoch
    dataset = Cifar10BinaryDataset(prepared_verification.directory, split="train")
    published: list[Path] = []
    try:
        for epoch in range(next_epoch, 301):
            set_epoch_learning_rate(optimizer, epoch)
            model.train()
            batches = 0
            samples = 0
            for batch_index, (cpu_inputs, cpu_targets) in enumerate(
                _training_loader(dataset, master_seed=request.master_seed, epoch=epoch)
            ):
                expected_size = 16 if batch_index == 781 else 64
                if tuple(cpu_inputs.shape) != (expected_size, 3, 32, 32):
                    raise RuntimeError("Formal training batch shape mismatch.")
                if tuple(cpu_targets.shape) != (expected_size,):
                    raise RuntimeError("Formal training target shape mismatch.")
                inputs = cpu_inputs.to(device, dtype=torch.float32, non_blocking=False)
                targets = cpu_targets.to(device, dtype=torch.long, non_blocking=False)
                optimizer.zero_grad(set_to_none=True)
                logits = model(inputs)
                loss = mean_cross_entropy(logits, targets)
                if not bool(torch.isfinite(loss)):
                    raise FloatingPointError("Formal loss is non-finite.")
                loss.backward()
                _require_all_finite(model, optimizer)
                accepted_step = (epoch - 1) * 782 + batch_index + 1
                execute_accounted_optimizer_call(
                    coordinates=FormalStepCoordinates(
                        request.master_seed, epoch, batch_index, accepted_step
                    ),
                    ledger=ledger,
                    optimizer_call=optimizer.step,
                    authorization=request.authorization,
                    expected_launch=request.expected_launch,
                    observed_launch=request.observed_launch,
                )
                _require_all_finite(model, optimizer)
                ledger_head = ledger.head_sha256
                _append_training_progress(
                    progress_path,
                    {
                        "accepted_step": accepted_step,
                        "batch_index": batch_index,
                        "classification": "FORMAL-TRAINING-PROGRESS-V1",
                        "epoch": epoch,
                        "ledger_head_sha256": ledger_head,
                        "loss_fp32_decimal": repr(float(loss.detach().cpu().item())),
                        "master_seed": request.master_seed,
                        "physical_completed_calls": ledger.summary().completed_calls,
                    },
                )
                batches += 1
                samples += expected_size
            if batches != 782 or samples != 50_000:
                raise RuntimeError("Formal epoch cardinality mismatch.")
            head = ledger.head_sha256
            checkpoint = run_root / f"epoch-{epoch:03d}.pt"
            save_formal_checkpoint(
                checkpoint_path=checkpoint,
                allowed_root=run_root,
                model=model,
                optimizer=optimizer,
                completed_epoch=epoch,
                master_seed=request.master_seed,
                attempt_summary=ledger.summary(),
                provenance=replace(request.base_provenance, ledger_head_sha256=head),
                cuda_device_indices=(request.device_index,),
            )
            published.append(checkpoint)
    finally:
        dataset.close()
    return tuple(published)
