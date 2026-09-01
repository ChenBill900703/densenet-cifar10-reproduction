from __future__ import annotations

import math
from unittest.mock import patch

import pytest
import torch
from torch import nn

from densenet_reproduction import (
    build_formal_model,
    initialize_densenet_parameters,
    state_dict_sha256,
)
from densenet_reproduction.model import convolution_init_std


TEST_ONLY_INITIALIZATION_SEED = 20_260_816
EXPECTED_INITIAL_STATE_SHA256 = "4DE22B2BF0305B716FC06671675221F2B56EE586A0FA059D639EE35367772CE4"


def test_explicit_initializer_calls_match_the_historical_rules() -> None:
    model = build_formal_model(test_seed=7)
    convolutions = [module for module in model.modules() if isinstance(module, nn.Conv2d)]

    with (
        patch("torch.nn.init.normal_") as normal,
        patch("torch.nn.init.uniform_") as uniform,
        patch("torch.nn.init.ones_") as ones,
        patch("torch.nn.init.zeros_") as zeros,
    ):
        initialize_densenet_parameters(model)

    assert normal.call_count == 99
    for call, convolution in zip(normal.call_args_list, convolutions, strict=True):
        assert call.args[0] is convolution.weight
        assert call.kwargs["mean"] == 0.0
        assert call.kwargs["std"] == convolution_init_std(convolution)

    assert uniform.call_count == 1
    classifier_call = uniform.call_args_list[0]
    expected_bound = 1.0 / math.sqrt(342)
    assert classifier_call.args[0] is model.classifier.weight
    assert classifier_call.args[1:] == (-expected_bound, expected_bound)
    assert ones.call_count == 99
    # 99 BN beta tensors plus the classifier bias are explicitly zeroed.
    assert zeros.call_count == 100


def test_batchnorm_and_classifier_initial_state_are_exact() -> None:
    model = build_formal_model(test_seed=8)
    for batch_norm in (
        module for module in model.modules() if isinstance(module, nn.BatchNorm2d)
    ):
        assert batch_norm.eps == 1e-5
        assert batch_norm.momentum == 0.1
        assert batch_norm.affine
        assert batch_norm.track_running_stats
        assert torch.equal(batch_norm.weight, torch.ones_like(batch_norm.weight))
        assert torch.equal(batch_norm.bias, torch.zeros_like(batch_norm.bias))
        assert torch.equal(batch_norm.running_mean, torch.zeros_like(batch_norm.running_mean))
        assert torch.equal(batch_norm.running_var, torch.ones_like(batch_norm.running_var))
        assert batch_norm.num_batches_tracked.item() == 0

    bound = 1.0 / math.sqrt(model.classifier.in_features)
    assert torch.all(model.classifier.weight >= -bound)
    assert torch.all(model.classifier.weight <= bound)
    assert torch.equal(model.classifier.bias, torch.zeros_like(model.classifier.bias))


def test_test_only_seed_is_deterministic_isolated_and_hash_locked() -> None:
    first = build_formal_model(test_seed=TEST_ONLY_INITIALIZATION_SEED)
    second = build_formal_model(test_seed=TEST_ONLY_INITIALIZATION_SEED)
    different = build_formal_model(test_seed=TEST_ONLY_INITIALIZATION_SEED + 1)

    assert state_dict_sha256(first) == EXPECTED_INITIAL_STATE_SHA256
    assert state_dict_sha256(second) == EXPECTED_INITIAL_STATE_SHA256
    assert state_dict_sha256(different) != EXPECTED_INITIAL_STATE_SHA256

    torch.manual_seed(91)
    expected_next_numbers = torch.rand(4)
    torch.manual_seed(91)
    build_formal_model(test_seed=TEST_ONLY_INITIALIZATION_SEED)
    actual_next_numbers = torch.rand(4)
    assert torch.equal(actual_next_numbers, expected_next_numbers)


def test_test_only_seed_preserves_every_initialized_cuda_rng() -> None:
    if not torch.cuda.is_available():
        pytest.skip("CUDA unavailable")
    original = torch.cuda.get_rng_state_all()
    try:
        torch.cuda.manual_seed_all(20_260_817)
        before = torch.cuda.get_rng_state_all()
        build_formal_model(test_seed=TEST_ONLY_INITIALIZATION_SEED)
        after = torch.cuda.get_rng_state_all()
        assert len(after) == len(before)
        assert all(torch.equal(old, new) for old, new in zip(before, after, strict=True))
    finally:
        torch.cuda.set_rng_state_all(original)


@pytest.mark.parametrize("bad_seed", [True, 1.5, "1"])
def test_test_only_seed_rejects_non_integer_values(bad_seed: object) -> None:
    with pytest.raises(TypeError, match="must be an integer"):
        build_formal_model(test_seed=bad_seed)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_seed", [-1, 2**64])
def test_test_only_seed_rejects_out_of_range_values(bad_seed: int) -> None:
    with pytest.raises(ValueError):
        build_formal_model(test_seed=bad_seed)


def test_batchnorm_uses_biased_batch_variance_and_unbiased_running_variance() -> None:
    batch_norm = nn.BatchNorm2d(
        1,
        eps=1e-5,
        momentum=0.1,
        affine=True,
        track_running_stats=True,
        dtype=torch.float64,
    )
    with torch.no_grad():
        batch_norm.weight.fill_(1.0)
        batch_norm.bias.zero_()
        batch_norm.running_mean.zero_()
        batch_norm.running_var.fill_(1.0)

    first = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=torch.float64).reshape(2, 1, 1, 2)
    first_output = batch_norm(first)
    first_mean = torch.tensor(2.5, dtype=torch.float64)
    first_biased_variance = torch.tensor(1.25, dtype=torch.float64)
    expected_first = (first - first_mean) / torch.sqrt(first_biased_variance + 1e-5)
    torch.testing.assert_close(first_output, expected_first, rtol=1e-12, atol=1e-12)
    torch.testing.assert_close(batch_norm.running_mean, torch.tensor([0.25], dtype=torch.float64))
    torch.testing.assert_close(
        batch_norm.running_var,
        torch.tensor([0.9 * 1.0 + 0.1 * (5.0 / 3.0)], dtype=torch.float64),
    )

    second = torch.tensor([2.0, 4.0, 6.0, 8.0], dtype=torch.float64).reshape(2, 1, 1, 2)
    second_output = batch_norm(second)
    second_mean = torch.tensor(5.0, dtype=torch.float64)
    second_biased_variance = torch.tensor(5.0, dtype=torch.float64)
    expected_second = (second - second_mean) / torch.sqrt(second_biased_variance + 1e-5)
    torch.testing.assert_close(second_output, expected_second, rtol=1e-12, atol=1e-12)
    expected_running_mean = 0.9 * 0.25 + 0.1 * 5.0
    expected_running_variance = 0.9 * (0.9 + 0.1 * (5.0 / 3.0)) + 0.1 * (20.0 / 3.0)
    torch.testing.assert_close(
        batch_norm.running_mean,
        torch.tensor([expected_running_mean], dtype=torch.float64),
    )
    torch.testing.assert_close(
        batch_norm.running_var,
        torch.tensor([expected_running_variance], dtype=torch.float64),
    )
    assert batch_norm.num_batches_tracked.item() == 2

    batch_norm.eval()
    evaluation = torch.tensor([[[[3.0]]]], dtype=torch.float64)
    expected_evaluation = (evaluation - expected_running_mean) / math.sqrt(
        expected_running_variance + 1e-5
    )
    torch.testing.assert_close(
        batch_norm(evaluation), expected_evaluation, rtol=1e-12, atol=1e-12
    )
