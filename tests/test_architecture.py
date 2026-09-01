from __future__ import annotations

import pytest
import torch
from torch import nn
from torch.nn import functional as F

from densenet_reproduction import (
    FORMAL_TARGET,
    DenseLayerBC,
    DenseNetBC100Cifar10,
    DenseNetCifarConfig,
    Transition,
    architecture_census,
    build_formal_model,
    parameter_breakdown,
)


def _trainable_parameters(module: nn.Module) -> int:
    return sum(parameter.numel() for parameter in module.parameters() if parameter.requires_grad)


def test_approved_target_identity_and_depth_formula() -> None:
    assert FORMAL_TARGET == DenseNetCifarConfig(
        depth=100,
        growth_rate=12,
        compression=0.5,
        bottleneck=True,
        dropout_rate=0.0,
        num_classes=10,
        input_channels=3,
        input_size=32,
        bn_eps=1e-5,
        bn_momentum=0.1,
        dtype=torch.float32,
    )
    assert FORMAL_TARGET.units_per_block == 16
    assert FORMAL_TARGET.initial_channels == 24
    assert FORMAL_TARGET.bottleneck_channels == 48
    assert 6 * FORMAL_TARGET.units_per_block + 4 == FORMAL_TARGET.depth


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"depth": 99}, r"6N \+ 4"),
        ({"bottleneck": False}, "restricted to DenseNet-BC"),
        ({"growth_rate": 0}, "positive"),
        ({"compression": 0.0}, "compression"),
        ({"dropout_rate": 1.0}, "dropout_rate"),
        ({"input_size": 224}, "N x 3 x 32 x 32"),
        ({"dtype": torch.float64}, "requires torch.float32"),
    ],
)
def test_invalid_configurations_fail_closed(
    override: dict[str, object], message: str
) -> None:
    values = {
        "depth": 100,
        "growth_rate": 12,
        "compression": 0.5,
        "bottleneck": True,
        "dropout_rate": 0.0,
        "num_classes": 10,
        "input_channels": 3,
        "input_size": 32,
        "bn_eps": 1e-5,
        "bn_momentum": 0.1,
        "dtype": torch.float32,
    }
    values.update(override)
    with pytest.raises(ValueError, match=message):
        DenseNetCifarConfig(**values)  # type: ignore[arg-type]


def test_model_rejects_an_unapproved_but_structurally_valid_target() -> None:
    other_target = DenseNetCifarConfig(depth=106)
    with pytest.raises(ValueError, match="locked to the approved"):
        DenseNetBC100Cifar10(other_target)


def test_model_construction_is_isolated_from_ambient_dtype_and_device() -> None:
    original_dtype = torch.get_default_dtype()
    original_device = torch.get_default_device()
    try:
        torch.set_default_dtype(torch.float64)
        torch.set_default_device("meta")
        model = build_formal_model(test_seed=20_260_816)
    finally:
        torch.set_default_device(original_device)
        torch.set_default_dtype(original_dtype)

    assert all(parameter.device.type == "cpu" for parameter in model.parameters())
    assert all(parameter.dtype == torch.float32 for parameter in model.parameters())
    assert all(
        buffer.dtype == torch.float32
        for buffer in model.buffers()
        if buffer.is_floating_point()
    )


def test_parameter_audit_rejects_shared_or_unclassified_parameters() -> None:
    tied = nn.Sequential(
        nn.Linear(2, 2, bias=False),
        nn.Linear(2, 2, bias=False),
    )
    tied[1].weight = tied[0].weight
    with pytest.raises(ValueError, match="Shared/tied"):
        parameter_breakdown(tied)

    class UnsupportedParameter(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.value = nn.Parameter(torch.ones(1))

    with pytest.raises(ValueError, match="did not cover"):
        parameter_breakdown(UnsupportedParameter())


def test_module_census_and_counted_depth_are_exact() -> None:
    model = build_formal_model(test_seed=1)
    assert architecture_census(model) == {
        "convolution": 99,
        "batch_norm": 99,
        "relu": 99,
        "average_pool": 3,
        "linear": 1,
        "dropout": 0,
        "counted_depth": 100,
    }
    assert len(model.block1.layers) == 16
    assert len(model.block2.layers) == 16
    assert len(model.block3.layers) == 16
    assert sum(isinstance(module, DenseLayerBC) for module in model.modules()) == 48
    assert not any(isinstance(module, (nn.Softmax, nn.LogSoftmax)) for module in model.modules())


def test_exact_parameter_ledger_and_bias_policy() -> None:
    model = build_formal_model(test_seed=2)
    assert parameter_breakdown(model) == {
        "convolution_weight": 741_744,
        "convolution_bias": 0,
        "batch_norm_affine": 23_988,
        "classifier_weight": 3_420,
        "classifier_bias": 10,
        "total": 769_162,
    }
    assert _trainable_parameters(model) == 769_162
    assert all(parameter.requires_grad for parameter in model.parameters())
    assert all(module.bias is None for module in model.modules() if isinstance(module, nn.Conv2d))
    assert model.classifier.bias is not None


def test_stage_parameter_ledger_is_exact() -> None:
    model = build_formal_model(test_seed=3)
    assert {
        "stem": _trainable_parameters(model.stem),
        "block1": _trainable_parameters(model.block1),
        "transition1": _trainable_parameters(model.transition1),
        "block2": _trainable_parameters(model.block2),
        "transition2": _trainable_parameters(model.transition2),
        "block3": _trainable_parameters(model.block3),
        "final_norm": _trainable_parameters(model.final_norm),
        "classifier": _trainable_parameters(model.classifier),
    } == {
        "stem": 648,
        "block1": 175_680,
        "transition1": 23_760,
        "block2": 242_880,
        "transition2": 45_600,
        "block3": 276_480,
        "final_norm": 684,
        "classifier": 3_430,
    }


def test_channel_and_spatial_shape_ledger_with_forward_hooks() -> None:
    model = build_formal_model(test_seed=4).eval()
    observed: dict[str, tuple[int, ...]] = {}
    handles = []
    for name in (
        "stem",
        "block1",
        "transition1",
        "block2",
        "transition2",
        "block3",
        "final_pool",
        "classifier",
    ):
        module = getattr(model, name)
        handles.append(
            module.register_forward_hook(
                lambda _module, _inputs, output, stage=name: observed.__setitem__(
                    stage, tuple(output.shape)
                )
            )
        )
    try:
        with torch.no_grad():
            logits = model(torch.zeros(2, 3, 32, 32))
    finally:
        for handle in handles:
            handle.remove()

    assert observed == {
        "stem": (2, 24, 32, 32),
        "block1": (2, 216, 32, 32),
        "transition1": (2, 108, 16, 16),
        "block2": (2, 300, 16, 16),
        "transition2": (2, 150, 8, 8),
        "block3": (2, 342, 8, 8),
        "final_pool": (2, 342, 1, 1),
        "classifier": (2, 10),
    }
    assert logits.shape == (2, 10)


def _functional_batch_norm_reference(
    inputs: torch.Tensor, module: nn.BatchNorm2d
) -> torch.Tensor:
    if module.training:
        module.num_batches_tracked.add_(1)
    return F.batch_norm(
        inputs,
        module.running_mean,
        module.running_var,
        module.weight,
        module.bias,
        training=module.training,
        momentum=module.momentum,
        eps=module.eps,
    )


def _functional_dense_layer_reference(
    inputs: torch.Tensor, layer: DenseLayerBC
) -> torch.Tensor:
    bottleneck = _functional_batch_norm_reference(inputs, layer.norm1)
    bottleneck = F.relu(bottleneck)
    bottleneck = F.conv2d(
        bottleneck,
        layer.conv1.weight,
        bias=None,
        stride=1,
        padding=0,
    )
    new_features = _functional_batch_norm_reference(bottleneck, layer.norm2)
    new_features = F.relu(new_features)
    new_features = F.conv2d(
        new_features,
        layer.conv2.weight,
        bias=None,
        stride=1,
        padding=1,
    )
    return torch.cat((inputs, new_features), dim=1)


def _functional_transition_reference(
    inputs: torch.Tensor, transition: Transition
) -> torch.Tensor:
    normalized = _functional_batch_norm_reference(inputs, transition.norm)
    activated = F.relu(normalized)
    compressed = F.conv2d(
        activated,
        transition.conv.weight,
        bias=None,
        stride=1,
        padding=0,
    )
    return F.avg_pool2d(compressed, kernel_size=2, stride=2)


@pytest.mark.parametrize("training", [False, True])
def test_forward_matches_independent_outer_graph_and_returns_raw_logits(
    training: bool,
) -> None:
    actual_model = build_formal_model(test_seed=19).train(training)
    reference_model = build_formal_model(test_seed=19).train(training)
    base_inputs = torch.randn(
        2, 3, 32, 32, generator=torch.Generator().manual_seed(20)
    )
    actual_inputs = base_inputs.clone().requires_grad_(True)
    reference_inputs = base_inputs.clone().requires_grad_(True)

    returned = actual_model(actual_inputs)
    features = F.conv2d(
        reference_inputs,
        reference_model.stem.weight,
        bias=None,
        stride=1,
        padding=1,
        dilation=1,
        groups=1,
    )
    for layer in reference_model.block1.layers:
        features = _functional_dense_layer_reference(features, layer)
    features = _functional_transition_reference(features, reference_model.transition1)
    for layer in reference_model.block2.layers:
        features = _functional_dense_layer_reference(features, layer)
    features = _functional_transition_reference(features, reference_model.transition2)
    for layer in reference_model.block3.layers:
        features = _functional_dense_layer_reference(features, layer)
    normalized = _functional_batch_norm_reference(features, reference_model.final_norm)
    activated = F.relu(normalized)
    pooled = F.avg_pool2d(activated, kernel_size=8, stride=8)
    expected_logits = F.linear(
        torch.flatten(pooled, 1),
        reference_model.classifier.weight,
        reference_model.classifier.bias,
    )
    assert torch.equal(returned, expected_logits)

    probe = torch.linspace(-0.7, 0.9, returned.numel()).reshape_as(returned)
    torch.sum(returned * probe).backward()
    torch.sum(expected_logits * probe).backward()
    assert actual_inputs.grad is not None
    assert reference_inputs.grad is not None
    assert torch.equal(actual_inputs.grad, reference_inputs.grad)
    actual_parameters = dict(actual_model.named_parameters())
    reference_parameters = dict(reference_model.named_parameters())
    assert actual_parameters.keys() == reference_parameters.keys()
    for name, actual_parameter in actual_parameters.items():
        reference_parameter = reference_parameters[name]
        assert actual_parameter.grad is not None, name
        assert reference_parameter.grad is not None, name
        assert torch.equal(actual_parameter.grad, reference_parameter.grad), name

    actual_state = actual_model.state_dict()
    reference_state = reference_model.state_dict()
    assert actual_state.keys() == reference_state.keys()
    assert all(
        torch.equal(actual_state[name], reference_state[name])
        for name in actual_state
    )


def test_dense_unit_preserves_old_channels_then_appends_twelve() -> None:
    layer = DenseLayerBC(input_channels=24, config=FORMAL_TARGET).eval()
    x = torch.randn(2, 24, 5, 5)
    with torch.no_grad():
        output = layer(x)
    assert output.shape == (2, 36, 5, 5)
    assert torch.equal(output[:, :24], x)


def test_all_forty_eight_units_preserve_their_accumulated_input_channels() -> None:
    model = build_formal_model(test_seed=17).eval()
    checks: list[bool] = []
    handles = []
    for module in model.modules():
        if isinstance(module, DenseLayerBC):
            handles.append(
                module.register_forward_hook(
                    lambda layer, inputs, output: checks.append(
                        output.shape[1] == layer.input_channels + 12
                        and torch.equal(output[:, : layer.input_channels], inputs[0])
                    )
                )
            )
    try:
        with torch.no_grad():
            model(torch.randn(1, 3, 32, 32))
    finally:
        for handle in handles:
            handle.remove()
    assert len(checks) == 48
    assert all(checks)


def test_pre_activation_and_transition_module_order_is_explicit() -> None:
    model = build_formal_model(test_seed=18)
    first_unit = model.block1.layers[0]
    assert list(first_unit._modules) == [
        "norm1",
        "relu1",
        "conv1",
        "norm2",
        "relu2",
        "conv2",
    ]
    assert first_unit.dropout1 is None
    assert first_unit.dropout2 is None
    assert list(model.transition1._modules) == ["norm", "relu", "conv", "pool"]
    assert model.transition1.dropout is None


def test_exact_bottleneck_width_compression_and_fixed_pool() -> None:
    model = build_formal_model(test_seed=5)
    assert all(layer.conv1.out_channels == 48 for layer in model.block1.layers)
    assert all(layer.conv2.out_channels == 12 for layer in model.block1.layers)
    assert (model.transition1.input_channels, model.transition1.output_channels) == (216, 108)
    assert (model.transition2.input_channels, model.transition2.output_channels) == (300, 150)
    assert model.output_channels == 342
    assert model.final_pool.kernel_size == 8
    assert model.final_pool.stride == 8


@pytest.mark.parametrize(
    "shape",
    [(3, 32, 32), (2, 1, 32, 32), (2, 3, 31, 32), (2, 3, 224, 224)],
)
def test_wrong_input_shape_is_rejected_before_execution(shape: tuple[int, ...]) -> None:
    model = build_formal_model(test_seed=6)
    with pytest.raises(ValueError, match="Expected N x 3 x 32 x 32"):
        model(torch.zeros(shape))
