"""Audited PyTorch mapping of the approved CIFAR-10 DenseNet target.

This module intentionally contains no dataset, optimizer, scheduler, checkpoint
selection, or accuracy-reporting code. Those belong to later gated phases.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import torch
from torch import Tensor, nn


@dataclass(frozen=True, slots=True)
class DenseNetCifarConfig:
    """Immutable architecture values for the approved formal target."""

    depth: int = 100
    growth_rate: int = 12
    compression: float = 0.5
    bottleneck: bool = True
    dropout_rate: float = 0.0
    num_classes: int = 10
    input_channels: int = 3
    input_size: int = 32
    bn_eps: float = 1e-5
    bn_momentum: float = 0.1
    dtype: torch.dtype = torch.float32

    def __post_init__(self) -> None:
        if not self.bottleneck:
            raise ValueError("This Phase 1 implementation is restricted to DenseNet-BC.")
        if self.depth < 10 or (self.depth - 4) % 6 != 0:
            raise ValueError("DenseNet-BC CIFAR depth must satisfy depth = 6N + 4.")
        if self.growth_rate <= 0:
            raise ValueError("growth_rate must be positive.")
        if not 0.0 < self.compression <= 1.0:
            raise ValueError("compression must be in (0, 1].")
        if not 0.0 <= self.dropout_rate < 1.0:
            raise ValueError("dropout_rate must be in [0, 1).")
        if self.num_classes <= 0:
            raise ValueError("num_classes must be positive.")
        if self.input_channels != 3 or self.input_size != 32:
            raise ValueError("The approved CIFAR target requires N x 3 x 32 x 32 input.")
        if self.bn_eps <= 0.0:
            raise ValueError("bn_eps must be positive.")
        if not 0.0 < self.bn_momentum <= 1.0:
            raise ValueError("bn_momentum must be in (0, 1].")
        if self.dtype is not torch.float32:
            raise ValueError("The approved formal target requires torch.float32.")

    @property
    def units_per_block(self) -> int:
        return (self.depth - 4) // 6

    @property
    def initial_channels(self) -> int:
        return 2 * self.growth_rate

    @property
    def bottleneck_channels(self) -> int:
        return 4 * self.growth_rate


FORMAL_TARGET = DenseNetCifarConfig()


def _batch_norm(channels: int, config: DenseNetCifarConfig) -> nn.BatchNorm2d:
    return nn.BatchNorm2d(
        channels,
        eps=config.bn_eps,
        momentum=config.bn_momentum,
        affine=True,
        track_running_stats=True,
        device="cpu",
        dtype=config.dtype,
    )


class DenseLayerBC(nn.Module):
    """One pre-activation bottleneck unit that appends exactly k channels."""

    def __init__(self, input_channels: int, config: DenseNetCifarConfig) -> None:
        super().__init__()
        self.input_channels = input_channels
        self.growth_rate = config.growth_rate
        bottleneck_channels = config.bottleneck_channels

        self.norm1 = _batch_norm(input_channels, config)
        self.relu1 = nn.ReLU(inplace=True)
        self.conv1 = nn.Conv2d(
            input_channels,
            bottleneck_channels,
            kernel_size=1,
            stride=1,
            padding=0,
            bias=False,
            device="cpu",
            dtype=config.dtype,
        )
        self.dropout1 = (
            nn.Dropout(p=config.dropout_rate) if config.dropout_rate > 0.0 else None
        )
        self.norm2 = _batch_norm(bottleneck_channels, config)
        self.relu2 = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(
            bottleneck_channels,
            config.growth_rate,
            kernel_size=3,
            stride=1,
            padding=1,
            bias=False,
            device="cpu",
            dtype=config.dtype,
        )
        self.dropout2 = (
            nn.Dropout(p=config.dropout_rate) if config.dropout_rate > 0.0 else None
        )

    def forward(self, x: Tensor) -> Tensor:
        new_features = self.conv1(self.relu1(self.norm1(x)))
        if self.dropout1 is not None:
            new_features = self.dropout1(new_features)
        new_features = self.conv2(self.relu2(self.norm2(new_features)))
        if self.dropout2 is not None:
            new_features = self.dropout2(new_features)
        return torch.cat((x, new_features), dim=1)


class DenseBlock(nn.Module):
    """A sequence of dense units with auditable channel growth."""

    def __init__(
        self,
        input_channels: int,
        units: int,
        config: DenseNetCifarConfig,
    ) -> None:
        super().__init__()
        layers: list[DenseLayerBC] = []
        channels = input_channels
        for _ in range(units):
            layers.append(DenseLayerBC(channels, config))
            channels += config.growth_rate
        self.layers = nn.ModuleList(layers)
        self.input_channels = input_channels
        self.output_channels = channels

    def forward(self, x: Tensor) -> Tensor:
        for layer in self.layers:
            x = layer(x)
        return x


class Transition(nn.Module):
    """BN-ReLU-1x1 convolution-compression followed by 2x2 average pool."""

    def __init__(
        self,
        input_channels: int,
        output_channels: int,
        config: DenseNetCifarConfig,
    ) -> None:
        super().__init__()
        self.input_channels = input_channels
        self.output_channels = output_channels
        self.norm = _batch_norm(input_channels, config)
        self.relu = nn.ReLU(inplace=True)
        self.conv = nn.Conv2d(
            input_channels,
            output_channels,
            kernel_size=1,
            stride=1,
            padding=0,
            bias=False,
            device="cpu",
            dtype=config.dtype,
        )
        self.dropout = (
            nn.Dropout(p=config.dropout_rate) if config.dropout_rate > 0.0 else None
        )
        self.pool = nn.AvgPool2d(kernel_size=2, stride=2)

    def forward(self, x: Tensor) -> Tensor:
        x = self.conv(self.relu(self.norm(x)))
        if self.dropout is not None:
            x = self.dropout(x)
        return self.pool(x)


class DenseNetBC100Cifar10(nn.Module):
    """DenseNet-BC-100-12 for the approved CIFAR-10+ target."""

    def __init__(self, config: DenseNetCifarConfig = FORMAL_TARGET) -> None:
        super().__init__()
        if config != FORMAL_TARGET:
            raise ValueError(
                "This class is locked to the approved Phase 1 target; a changed "
                "configuration requires a documented target decision."
            )
        self.config = config

        channels = config.initial_channels
        self.stem = nn.Conv2d(
            config.input_channels,
            channels,
            kernel_size=3,
            stride=1,
            padding=1,
            bias=False,
            device="cpu",
            dtype=config.dtype,
        )

        self.block1 = DenseBlock(channels, config.units_per_block, config)
        channels = self.block1.output_channels
        transition1_channels = math.floor(channels * config.compression)
        self.transition1 = Transition(channels, transition1_channels, config)

        channels = transition1_channels
        self.block2 = DenseBlock(channels, config.units_per_block, config)
        channels = self.block2.output_channels
        transition2_channels = math.floor(channels * config.compression)
        self.transition2 = Transition(channels, transition2_channels, config)

        channels = transition2_channels
        self.block3 = DenseBlock(channels, config.units_per_block, config)
        channels = self.block3.output_channels

        self.final_norm = _batch_norm(channels, config)
        self.final_relu = nn.ReLU(inplace=True)
        self.final_pool = nn.AvgPool2d(kernel_size=8, stride=8)
        self.classifier = nn.Linear(
            channels,
            config.num_classes,
            bias=True,
            device="cpu",
            dtype=config.dtype,
        )
        self.output_channels = channels

        initialize_densenet_parameters(self)

    def _validate_input(self, x: Tensor) -> None:
        expected = (
            "N x "
            f"{self.config.input_channels} x {self.config.input_size} x "
            f"{self.config.input_size}"
        )
        if x.ndim != 4:
            raise ValueError(f"Expected {expected} input, got a {x.ndim}-D tensor.")
        if tuple(x.shape[1:]) != (
            self.config.input_channels,
            self.config.input_size,
            self.config.input_size,
        ):
            raise ValueError(f"Expected {expected} input, got shape {tuple(x.shape)}.")

    def forward_features(self, x: Tensor) -> Tensor:
        self._validate_input(x)
        x = self.stem(x)
        x = self.block1(x)
        x = self.transition1(x)
        x = self.block2(x)
        x = self.transition2(x)
        return self.block3(x)

    def forward(self, x: Tensor) -> Tensor:
        x = self.forward_features(x)
        x = self.final_pool(self.final_relu(self.final_norm(x)))
        x = torch.flatten(x, 1)
        return self.classifier(x)


def convolution_init_std(module: nn.Conv2d) -> float:
    """Official Torch7 fan-out initialization standard deviation."""

    kernel_height, kernel_width = module.kernel_size
    return math.sqrt(2.0 / (kernel_height * kernel_width * module.out_channels))


@torch.no_grad()
def initialize_densenet_parameters(module: nn.Module) -> None:
    """Apply every historical initialization rule explicitly.

    The classifier rule is the historical Torch nn.Linear reset rule from the
    date-aligned dependency candidate; it is not delegated to PyTorch defaults.
    """

    for child in module.modules():
        if isinstance(child, nn.Conv2d):
            nn.init.normal_(child.weight, mean=0.0, std=convolution_init_std(child))
            if child.bias is not None:
                nn.init.zeros_(child.bias)
        elif isinstance(child, nn.BatchNorm2d):
            nn.init.ones_(child.weight)
            nn.init.zeros_(child.bias)
            child.running_mean.zero_()
            child.running_var.fill_(1.0)
            child.num_batches_tracked.zero_()
        elif isinstance(child, nn.Linear):
            bound = 1.0 / math.sqrt(child.in_features)
            nn.init.uniform_(child.weight, -bound, bound)
            if child.bias is not None:
                nn.init.zeros_(child.bias)


def build_formal_model(*, test_seed: int | None = None) -> DenseNetBC100Cifar10:
    """Build the approved architecture, optionally under an isolated test seed.

    ``test_seed`` exists for Phase 1 regression tests only. It is not a paper
    seed and must not be described as a preregistered reproduction seed.
    """

    if test_seed is None:
        return DenseNetBC100Cifar10(FORMAL_TARGET)
    if isinstance(test_seed, bool) or not isinstance(test_seed, int):
        raise TypeError("test_seed must be an integer.")
    if test_seed < 0:
        raise ValueError("test_seed must be non-negative.")
    if test_seed > 0xFFFF_FFFF_FFFF_FFFF:
        raise ValueError("test_seed must fit in an unsigned 64-bit integer.")
    with torch.random.fork_rng(devices=[]):
        # Seed only the CPU generator used by the explicitly CPU-constructed
        # modules. torch.manual_seed would also alter every CUDA RNG state.
        torch.random.default_generator.manual_seed(test_seed)
        return DenseNetBC100Cifar10(FORMAL_TARGET)
