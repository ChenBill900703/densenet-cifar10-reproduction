"""Read-only audit helpers for the Phase 1 model."""

from __future__ import annotations

import hashlib
import json

import torch
from torch import nn


def architecture_census(model: nn.Module) -> dict[str, int]:
    """Count modules using the depth convention documented by the paper/code."""

    counts = {
        "convolution": 0,
        "batch_norm": 0,
        "relu": 0,
        "average_pool": 0,
        "linear": 0,
        "dropout": 0,
    }
    for module in model.modules():
        if isinstance(module, nn.Conv2d):
            counts["convolution"] += 1
        elif isinstance(module, nn.BatchNorm2d):
            counts["batch_norm"] += 1
        elif isinstance(module, nn.ReLU):
            counts["relu"] += 1
        elif isinstance(module, nn.AvgPool2d):
            counts["average_pool"] += 1
        elif isinstance(module, nn.Linear):
            counts["linear"] += 1
        elif isinstance(module, nn.Dropout):
            counts["dropout"] += 1
    counts["counted_depth"] = counts["convolution"] + counts["linear"]
    return counts


def parameter_breakdown(model: nn.Module) -> dict[str, int]:
    """Account for every trainable parameter exactly once by historical role."""

    breakdown = {
        "convolution_weight": 0,
        "convolution_bias": 0,
        "batch_norm_affine": 0,
        "classifier_weight": 0,
        "classifier_bias": 0,
    }
    seen: set[int] = set()

    def add_parameter(category: str, parameter: nn.Parameter) -> None:
        identity = id(parameter)
        if identity in seen:
            raise ValueError(
                "Shared/tied trainable parameters are outside the approved "
                "architecture and cannot be counted twice."
            )
        seen.add(identity)
        breakdown[category] += parameter.numel()

    for module in model.modules():
        if isinstance(module, nn.Conv2d):
            add_parameter("convolution_weight", module.weight)
            if module.bias is not None:
                add_parameter("convolution_bias", module.bias)
        elif isinstance(module, nn.BatchNorm2d):
            if module.weight is None or module.bias is None:
                raise ValueError("The approved architecture requires affine BatchNorm.")
            add_parameter("batch_norm_affine", module.weight)
            add_parameter("batch_norm_affine", module.bias)
        elif isinstance(module, nn.Linear):
            add_parameter("classifier_weight", module.weight)
            if module.bias is not None:
                add_parameter("classifier_bias", module.bias)

    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if len(seen) != len(trainable) or seen != {id(parameter) for parameter in trainable}:
        raise ValueError("Parameter accounting did not cover every trainable tensor once.")
    breakdown["total"] = sum(breakdown.values())
    return breakdown


def state_dict_sha256(model: nn.Module) -> str:
    """Hash names, dtypes, shapes, and canonical CPU bytes of the full state."""

    digest = hashlib.sha256()
    for name, tensor in model.state_dict().items():
        cpu_tensor = tensor.detach().cpu().contiguous()
        metadata = json.dumps(
            {
                "name": name,
                "dtype": str(cpu_tensor.dtype),
                "shape": list(cpu_tensor.shape),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest.update(len(metadata).to_bytes(8, byteorder="little", signed=False))
        digest.update(metadata)
        # Avoid an undeclared NumPy dependency: reinterpret the contiguous
        # tensor storage as bytes using only PyTorch and Python primitives.
        raw_bytes = bytes(cpu_tensor.reshape(-1).view(torch.uint8).tolist())
        digest.update(raw_bytes)
    return digest.hexdigest().upper()
