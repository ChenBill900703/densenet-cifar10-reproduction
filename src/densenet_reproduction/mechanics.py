"""Human-approved Phase 3 mechanics restricted to generated data.

Nothing in this module reads CIFAR, computes predictions/accuracy, or represents
a formal optimizer step.  The only stepping API requires a batch created by the
generated-data factory below and increments a separate synthetic-step ledger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import random
from typing import Callable, Final

import torch
from torch import Tensor, nn

from .model import DenseNetBC100Cifar10, FORMAL_TARGET


PROJECT_REPRODUCTION_SEEDS: Final[tuple[int, int, int]] = (
    1_021_082_110,
    1_747_066_946,
    869_460_408,
)
SEED_MASK_63: Final[int] = (1 << 63) - 1
MODEL_INIT_DOMAIN: Final[str] = "densenet-model-init-v1"
PYTHON_RUNTIME_DOMAIN: Final[str] = "densenet-python-runtime-v1"
TORCH_CPU_RUNTIME_DOMAIN: Final[str] = "densenet-torch-cpu-runtime-v1"
TORCH_CUDA_RUNTIME_DOMAIN: Final[str] = "densenet-torch-cuda-runtime-v1"
LOADER_WORKER_BASE_DOMAIN: Final[str] = "densenet-loader-worker-base-v1"
LR_POLICY_ID: Final[str] = "densenet-cifar300-multistep-v1"
RNG_POLICY_ID: Final[str] = "densenet-runtime-rng-v1"
OPTIMIZER_POLICY_ID: Final[str] = "densenet-historical-sgd-v1"
LOSS_POLICY_ID: Final[str] = "densenet-mean-cross-entropy-v1"
SYNTHETIC_CLASSIFICATION: Final[str] = (
    "NON-FORMAL-SYNTHETIC-OPTIMIZER-MECHANICS"
)

_GENERATED_BATCH_TOKEN = object()


def _require_plain_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer.")
    return value


def require_project_master_seed(master_seed: int) -> int:
    """Fail unless ``master_seed`` is one of the three preregistered seeds."""

    value = _require_plain_int(master_seed, "master_seed")
    if value not in PROJECT_REPRODUCTION_SEEDS:
        raise ValueError("master_seed is not a preregistered project seed.")
    return value


def derive_domain_seed(domain: str, master_seed: int, *coordinates: int) -> int:
    """Derive one 63-bit seed from the approved UTF-8/SHA256 mapping."""

    if not isinstance(domain, str) or not domain or "|" in domain:
        raise ValueError("domain must be a non-empty string without '|'.")
    seed = require_project_master_seed(master_seed)
    fields = [domain, str(seed)]
    for index, coordinate in enumerate(coordinates):
        value = _require_plain_int(coordinate, f"coordinate[{index}]")
        if value < 0:
            raise ValueError("seed coordinates must be non-negative.")
        fields.append(str(value))
    digest = hashlib.sha256("|".join(fields).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) & SEED_MASK_63


@dataclass(frozen=True, slots=True)
class RuntimeSeedBundle:
    """All non-data global runtime seeds for one project master seed."""

    master_seed: int
    model_init: int
    python_runtime: int
    torch_cpu_runtime: int
    torch_cuda_runtime: tuple[tuple[int, int], ...]


def runtime_seed_bundle(
    master_seed: int, *, cuda_device_indices: tuple[int, ...] = ()
) -> RuntimeSeedBundle:
    """Return the approved domain-separated seed bundle without changing RNGs."""

    seed = require_project_master_seed(master_seed)
    if len(set(cuda_device_indices)) != len(cuda_device_indices):
        raise ValueError("cuda_device_indices must be unique.")
    cuda_seeds: list[tuple[int, int]] = []
    for index in cuda_device_indices:
        device_index = _require_plain_int(index, "CUDA device index")
        if device_index < 0:
            raise ValueError("CUDA device indices must be non-negative.")
        cuda_seeds.append(
            (
                device_index,
                derive_domain_seed(TORCH_CUDA_RUNTIME_DOMAIN, seed, device_index),
            )
        )
    return RuntimeSeedBundle(
        master_seed=seed,
        model_init=derive_domain_seed(MODEL_INIT_DOMAIN, seed),
        python_runtime=derive_domain_seed(PYTHON_RUNTIME_DOMAIN, seed),
        torch_cpu_runtime=derive_domain_seed(TORCH_CPU_RUNTIME_DOMAIN, seed),
        torch_cuda_runtime=tuple(cuda_seeds),
    )


def loader_worker_base_seed(master_seed: int, epoch: int) -> int:
    """Derive the approved worker-bootstrap seed for one epoch."""

    epoch_value = _require_plain_int(epoch, "epoch")
    if not 1 <= epoch_value <= 300:
        raise ValueError("epoch must be in [1, 300].")
    return derive_domain_seed(LOADER_WORKER_BASE_DOMAIN, master_seed, epoch_value)


def build_project_seeded_model(master_seed: int) -> DenseNetBC100Cifar10:
    """Build the formal model under its isolated approved initialization seed."""

    bundle = runtime_seed_bundle(master_seed)
    with torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(bundle.model_init)
        return DenseNetBC100Cifar10(FORMAL_TARGET)


def initialize_runtime_rngs(bundle: RuntimeSeedBundle) -> None:
    """Set Python, CPU, and explicitly named CUDA RNGs from one seed bundle."""

    expected = runtime_seed_bundle(
        bundle.master_seed,
        cuda_device_indices=tuple(index for index, _ in bundle.torch_cuda_runtime),
    )
    if bundle != expected:
        raise ValueError("RuntimeSeedBundle does not match the approved derivation.")
    random.seed(bundle.python_runtime)
    torch.random.default_generator.manual_seed(bundle.torch_cpu_runtime)
    if bundle.torch_cuda_runtime:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA seeds were requested but CUDA is unavailable.")
        device_count = torch.cuda.device_count()
        for device_index, seed in bundle.torch_cuda_runtime:
            if device_index >= device_count:
                raise ValueError(f"CUDA device index {device_index} is unavailable.")
            generator = torch.Generator(device=f"cuda:{device_index}")
            generator.manual_seed(seed)
            torch.cuda.set_rng_state(generator.get_state(), device=device_index)


def learning_rate_for_epoch(epoch: int) -> float:
    """Return the official 300-epoch multistep rate without scheduler state."""

    value = _require_plain_int(epoch, "epoch")
    if not 1 <= value <= 300:
        raise ValueError("epoch must be in [1, 300].")
    if value < 150:
        return 0.1
    if value < 225:
        return 0.01
    return 0.001


def _trainable_parameters_once(model: nn.Module) -> list[nn.Parameter]:
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if len(parameters) != 299:
        raise ValueError("The approved model must expose exactly 299 trainable tensors.")
    identities = [id(parameter) for parameter in parameters]
    if len(set(identities)) != len(identities):
        raise ValueError("Shared/tied parameters are forbidden in the optimizer.")
    if any(parameter.dtype is not torch.float32 for parameter in parameters):
        raise ValueError("Every optimized parameter must be FP32.")
    return parameters


def build_phase3_optimizer(
    model: DenseNetBC100Cifar10, *, epoch: int = 1
) -> torch.optim.SGD:
    """Build the approved one-group SGD for synthetic Phase 3 validation."""

    if not isinstance(model, DenseNetBC100Cifar10) or model.config != FORMAL_TARGET:
        raise TypeError("Phase 3 optimizer requires the approved formal model.")
    parameters = _trainable_parameters_once(model)
    return torch.optim.SGD(
        parameters,
        lr=learning_rate_for_epoch(epoch),
        momentum=0.9,
        dampening=0.0,
        weight_decay=1e-4,
        nesterov=True,
        maximize=False,
        foreach=False,
        differentiable=False,
        fused=False,
    )


def validate_phase3_optimizer(
    model: DenseNetBC100Cifar10, optimizer: torch.optim.Optimizer
) -> None:
    """Fail unless the optimizer exactly matches A-009 and the model order."""

    if type(optimizer) is not torch.optim.SGD:
        raise TypeError("The approved optimizer type is exactly torch.optim.SGD.")
    parameters = _trainable_parameters_once(model)
    if len(optimizer.param_groups) != 1:
        raise ValueError("The approved optimizer has exactly one parameter group.")
    group = optimizer.param_groups[0]
    if [id(value) for value in group["params"]] != [id(value) for value in parameters]:
        raise ValueError("Optimizer parameter coverage/order does not match the model.")
    expected = {
        "momentum": 0.9,
        "dampening": 0.0,
        "weight_decay": 1e-4,
        "nesterov": True,
        "maximize": False,
        "foreach": False,
        "differentiable": False,
        "fused": False,
    }
    for key, value in expected.items():
        if group.get(key) != value:
            raise ValueError(f"Unexpected optimizer setting {key}={group.get(key)!r}.")
    if group.get("lr") not in (0.1, 0.01, 0.001):
        raise ValueError("Optimizer learning rate is outside the approved schedule.")


def set_epoch_learning_rate(optimizer: torch.optim.Optimizer, epoch: int) -> float:
    """Assign and return the approved LR for ``epoch``."""

    if len(optimizer.param_groups) != 1:
        raise ValueError("Learning-rate assignment requires exactly one parameter group.")
    learning_rate = learning_rate_for_epoch(epoch)
    optimizer.param_groups[0]["lr"] = learning_rate
    return learning_rate


def mean_cross_entropy(logits: Tensor, targets: Tensor) -> Tensor:
    """Historical unweighted batch-mean cross-entropy on raw logits."""

    if logits.ndim != 2 or logits.shape[1] != FORMAL_TARGET.num_classes:
        raise ValueError("logits must have shape [N, 10].")
    if logits.dtype is not torch.float32:
        raise ValueError("Phase 3 logits must be FP32.")
    if targets.ndim != 1 or targets.shape[0] != logits.shape[0]:
        raise ValueError("targets must have shape [N] matching logits.")
    if targets.dtype is not torch.long:
        raise ValueError("targets must use torch.long.")
    if targets.device != logits.device:
        raise ValueError("logits and targets must be on the same device.")
    if targets.numel() == 0:
        raise ValueError("The physical batch must be non-empty.")
    if bool(((targets < 0) | (targets >= FORMAL_TARGET.num_classes)).any()):
        raise ValueError("targets must be in [0, 9].")
    return nn.functional.cross_entropy(
        logits,
        targets,
        weight=None,
        reduction="mean",
        label_smoothing=0.0,
    )


@dataclass(frozen=True, slots=True)
class SyntheticMechanicsBatch:
    """A generated-only input/target pair accepted by the stepping API."""

    inputs: Tensor
    targets: Tensor
    generation_seed: int
    classification: str
    _authorization: object = field(repr=False, compare=False)


def make_synthetic_mechanics_batch(
    *, batch_size: int, generation_seed: int, device: torch.device | str
) -> SyntheticMechanicsBatch:
    """Generate a batch locally; this factory never reads a dataset."""

    size = _require_plain_int(batch_size, "batch_size")
    seed = _require_plain_int(generation_seed, "generation_seed")
    if size < 2:
        raise ValueError("Synthetic train-mode BatchNorm checks require batch_size >= 2.")
    if seed < 0 or seed > 0xFFFF_FFFF_FFFF_FFFF:
        raise ValueError("generation_seed must fit in an unsigned 64-bit integer.")
    generator = torch.Generator(device="cpu").manual_seed(seed)
    inputs = torch.randn(
        size,
        FORMAL_TARGET.input_channels,
        FORMAL_TARGET.input_size,
        FORMAL_TARGET.input_size,
        generator=generator,
        dtype=torch.float32,
    ).to(device)
    targets = torch.randint(
        0,
        FORMAL_TARGET.num_classes,
        (size,),
        generator=generator,
        dtype=torch.long,
    ).to(device)
    return SyntheticMechanicsBatch(
        inputs=inputs,
        targets=targets,
        generation_seed=seed,
        classification=SYNTHETIC_CLASSIFICATION,
        _authorization=_GENERATED_BATCH_TOKEN,
    )


@dataclass(slots=True)
class SyntheticStepLedger:
    """Separate synthetic mechanics steps from the immutable formal count."""

    synthetic_optimizer_steps: int = 0
    formal_optimizer_steps: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        value = _require_plain_int(
            self.synthetic_optimizer_steps, "synthetic_optimizer_steps"
        )
        if value < 0:
            raise ValueError("synthetic_optimizer_steps must be non-negative.")


def synthetic_mechanics_step(
    *,
    model: DenseNetBC100Cifar10,
    optimizer: torch.optim.Optimizer,
    batch: SyntheticMechanicsBatch,
    epoch: int,
    ledger: SyntheticStepLedger,
    stage_callback: Callable[[str], None] | None = None,
) -> Tensor:
    """Execute one generated-data-only, explicitly non-formal optimizer step."""

    if batch._authorization is not _GENERATED_BATCH_TOKEN:
        raise ValueError("Only factory-generated Phase 3 batches may be stepped.")
    if batch.classification != SYNTHETIC_CLASSIFICATION:
        raise ValueError("Synthetic batch classification is invalid.")
    if ledger.formal_optimizer_steps != 0:
        raise ValueError("Formal optimizer steps are forbidden in Phase 3.")
    validate_phase3_optimizer(model, optimizer)
    if next(model.parameters()).device != batch.inputs.device:
        raise ValueError("Model and generated batch must be on the same device.")
    set_epoch_learning_rate(optimizer, epoch)
    model.train()
    optimizer.zero_grad(set_to_none=True)
    logits = model(batch.inputs)
    if stage_callback is not None:
        stage_callback("forward")
    loss = mean_cross_entropy(logits, batch.targets)
    if not bool(torch.isfinite(loss)):
        raise FloatingPointError("Synthetic loss is non-finite.")
    loss.backward()
    if stage_callback is not None:
        stage_callback("backward")
    for name, parameter in model.named_parameters():
        if parameter.grad is None:
            raise RuntimeError(f"Missing gradient for {name}.")
        if not bool(torch.isfinite(parameter.grad).all()):
            raise FloatingPointError(f"Non-finite gradient for {name}.")
    optimizer.step()
    if stage_callback is not None:
        stage_callback("optimizer_update")
    for name, tensor in model.state_dict().items():
        if not bool(torch.isfinite(tensor).all()):
            raise FloatingPointError(f"Non-finite model state after step: {name}.")
    for state in optimizer.state.values():
        for value in state.values():
            if isinstance(value, Tensor) and not bool(torch.isfinite(value).all()):
                raise FloatingPointError("Non-finite optimizer state after step.")
    ledger.synthetic_optimizer_steps += 1
    return loss.detach().clone()
