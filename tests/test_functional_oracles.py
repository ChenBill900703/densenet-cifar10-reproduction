from __future__ import annotations

import pytest
import torch
from torch import nn
from torch.nn import functional as F

from densenet_reproduction import (
    FORMAL_TARGET,
    DenseLayerBC,
    Transition,
    build_formal_model,
)


def _set_nontrivial_batch_norm_state(module: nn.BatchNorm2d) -> None:
    channels = module.num_features
    with torch.no_grad():
        module.weight.copy_(torch.linspace(0.6, 1.4, channels, dtype=module.weight.dtype))
        module.bias.copy_(torch.linspace(-0.3, 0.2, channels, dtype=module.bias.dtype))
        module.running_mean.copy_(
            torch.linspace(-0.5, 0.4, channels, dtype=module.running_mean.dtype)
        )
        module.running_var.copy_(
            torch.linspace(0.7, 1.6, channels, dtype=module.running_var.dtype)
        )


def _set_nontrivial_convolution_weight(module: nn.Conv2d) -> None:
    with torch.no_grad():
        values = torch.linspace(
            -0.25,
            0.35,
            module.weight.numel(),
            dtype=module.weight.dtype,
        )
        module.weight.copy_(values.reshape_as(module.weight))


def _functional_batch_norm(x: torch.Tensor, module: nn.BatchNorm2d) -> torch.Tensor:
    if module.training:
        module.num_batches_tracked.add_(1)
    return F.batch_norm(
        x,
        module.running_mean,
        module.running_var,
        module.weight,
        module.bias,
        training=module.training,
        momentum=module.momentum,
        eps=module.eps,
    )


def _assert_same_state(actual: nn.Module, reference: nn.Module) -> None:
    actual_state = actual.state_dict()
    reference_state = reference.state_dict()
    assert actual_state.keys() == reference_state.keys()
    assert all(
        torch.equal(actual_state[name], reference_state[name])
        for name in actual_state
    )


def test_stem_execution_matches_independent_zero_padding_reference() -> None:
    stem = build_formal_model(test_seed=21).stem.double()
    _set_nontrivial_convolution_weight(stem)
    inputs = torch.linspace(-1.1, 1.4, 3 * 5 * 6, dtype=torch.float64).reshape(
        1, 3, 5, 6
    )

    assert stem.kernel_size == (3, 3)
    assert stem.stride == (1, 1)
    assert stem.padding == (1, 1)
    assert stem.padding_mode == "zeros"
    assert stem.dilation == (1, 1)
    assert stem.groups == 1
    assert stem.bias is None
    expected = F.conv2d(
        inputs,
        stem.weight,
        bias=None,
        stride=1,
        padding=1,
        dilation=1,
        groups=1,
    )

    with torch.no_grad():
        actual = stem(inputs)
    torch.testing.assert_close(actual, expected, rtol=0.0, atol=0.0)


@pytest.mark.parametrize("training", [False, True])
def test_dense_layer_execution_matches_independent_pre_activation_reference(
    training: bool,
) -> None:
    actual = DenseLayerBC(input_channels=3, config=FORMAL_TARGET).double()
    _set_nontrivial_batch_norm_state(actual.norm1)
    _set_nontrivial_batch_norm_state(actual.norm2)
    _set_nontrivial_convolution_weight(actual.conv1)
    _set_nontrivial_convolution_weight(actual.conv2)
    reference = DenseLayerBC(input_channels=3, config=FORMAL_TARGET).double()
    reference.load_state_dict(actual.state_dict(), strict=True)
    actual.train(training)
    reference.train(training)
    inputs = torch.linspace(-1.2, 1.1, 3 * 4 * 4, dtype=torch.float64).reshape(
        1, 3, 4, 4
    )

    with torch.no_grad():
        actual_output = actual(inputs)
        bottleneck = _functional_batch_norm(inputs, reference.norm1)
        bottleneck = F.relu(bottleneck)
        bottleneck = F.conv2d(
            bottleneck,
            reference.conv1.weight,
            bias=None,
            stride=1,
            padding=0,
        )
        new_features = _functional_batch_norm(bottleneck, reference.norm2)
        new_features = F.relu(new_features)
        new_features = F.conv2d(
            new_features,
            reference.conv2.weight,
            bias=None,
            stride=1,
            padding=1,
        )
        expected = torch.cat((inputs, new_features), dim=1)
    torch.testing.assert_close(actual_output, expected, rtol=0.0, atol=0.0)
    _assert_same_state(actual, reference)


@pytest.mark.parametrize("training", [False, True])
def test_transition_execution_matches_independent_pre_activation_reference(
    training: bool,
) -> None:
    actual = Transition(
        input_channels=5,
        output_channels=3,
        config=FORMAL_TARGET,
    ).double()
    _set_nontrivial_batch_norm_state(actual.norm)
    _set_nontrivial_convolution_weight(actual.conv)
    reference = Transition(
        input_channels=5,
        output_channels=3,
        config=FORMAL_TARGET,
    ).double()
    reference.load_state_dict(actual.state_dict(), strict=True)
    actual.train(training)
    reference.train(training)
    inputs = torch.linspace(-1.0, 1.3, 5 * 6 * 6, dtype=torch.float64).reshape(
        1, 5, 6, 6
    )

    with torch.no_grad():
        actual_output = actual(inputs)
        expected = _functional_batch_norm(inputs, reference.norm)
        expected = F.relu(expected)
        expected = F.conv2d(
            expected,
            reference.conv.weight,
            bias=None,
            stride=1,
            padding=0,
        )
        expected = F.avg_pool2d(expected, kernel_size=2, stride=2)
    torch.testing.assert_close(actual_output, expected, rtol=0.0, atol=0.0)
    _assert_same_state(actual, reference)
