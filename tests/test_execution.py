from __future__ import annotations

import io

import torch
from torch import nn

from densenet_reproduction import (
    FORMAL_TARGET,
    DenseLayerBC,
    build_formal_model,
    state_dict_sha256,
)


def test_synthetic_forward_and_backward_reach_every_parameter() -> None:
    model = build_formal_model(test_seed=11).train()
    generator = torch.Generator().manual_seed(12)
    inputs = torch.randn(2, 3, 32, 32, generator=generator)
    targets = torch.tensor([0, 9], dtype=torch.long)

    logits = model(inputs)
    loss = nn.functional.cross_entropy(logits, targets)
    loss.backward()

    assert logits.shape == (2, 10)
    assert torch.isfinite(logits).all()
    assert torch.isfinite(loss)
    for name, parameter in model.named_parameters():
        assert parameter.grad is not None, f"missing gradient: {name}"
        assert torch.isfinite(parameter.grad).all(), f"non-finite gradient: {name}"


def test_small_dense_unit_passes_double_precision_input_gradcheck() -> None:
    layer = DenseLayerBC(input_channels=3, config=FORMAL_TARGET).double().eval()
    for parameter in layer.parameters():
        parameter.requires_grad_(False)
    input_tensor = torch.randn(
        1,
        3,
        2,
        2,
        dtype=torch.float64,
        requires_grad=True,
        generator=torch.Generator().manual_seed(13),
    )
    assert torch.autograd.gradcheck(
        layer,
        (input_tensor,),
        eps=1e-6,
        atol=1e-4,
        rtol=1e-3,
        raise_exception=True,
    )


def test_state_dict_round_trip_preserves_logits_and_all_buffers() -> None:
    source = build_formal_model(test_seed=14).train()
    restored = build_formal_model(test_seed=15).eval()

    # Exercise every BN running-stat buffer before serialization.
    update_inputs = torch.randn(
        2, 3, 32, 32, generator=torch.Generator().manual_seed(15)
    )
    with torch.no_grad():
        source(update_inputs)
    assert all(
        module.num_batches_tracked.item() == 1
        for module in source.modules()
        if isinstance(module, nn.BatchNorm2d)
    )

    serialized = io.BytesIO()
    torch.save(source.state_dict(), serialized)
    serialized.seek(0)
    restored.load_state_dict(
        torch.load(serialized, map_location="cpu", weights_only=True), strict=True
    )
    source.eval()

    inputs = torch.randn(2, 3, 32, 32, generator=torch.Generator().manual_seed(16))
    with torch.no_grad():
        source_logits = source(inputs)
        restored_logits = restored(inputs)

    assert torch.equal(source_logits, restored_logits)
    assert state_dict_sha256(source) == state_dict_sha256(restored)
    for name, source_value in source.state_dict().items():
        assert torch.equal(source_value, restored.state_dict()[name]), name
