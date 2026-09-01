from __future__ import annotations

import hashlib
import random

import pytest
import torch

from densenet_reproduction import (
    PROJECT_REPRODUCTION_SEEDS,
    RuntimeSeedBundle,
    SyntheticMechanicsBatch,
    SyntheticStepLedger,
    build_phase3_optimizer,
    build_project_seeded_model,
    derive_domain_seed,
    initialize_runtime_rngs,
    learning_rate_for_epoch,
    loader_worker_base_seed,
    make_synthetic_mechanics_batch,
    mean_cross_entropy,
    runtime_seed_bundle,
    set_epoch_learning_rate,
    state_dict_sha256,
    synthetic_mechanics_step,
    validate_phase3_optimizer,
)


@pytest.mark.parametrize(
    ("epoch", "expected"),
    [(1, 0.1), (149, 0.1), (150, 0.01), (224, 0.01), (225, 0.001), (300, 0.001)],
)
def test_epoch_learning_rate_boundaries_are_explicit(epoch: int, expected: float) -> None:
    assert learning_rate_for_epoch(epoch) == expected


@pytest.mark.parametrize("epoch", [0, 301, -1, True, 1.0])
def test_epoch_learning_rate_rejects_out_of_contract_values(epoch: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        learning_rate_for_epoch(epoch)  # type: ignore[arg-type]


def test_seed_derivation_matches_an_independent_sha256_calculation() -> None:
    master_seed = PROJECT_REPRODUCTION_SEEDS[0]

    def independent(domain: str, *coordinates: int) -> int:
        message = "|".join(
            [domain, str(master_seed), *(str(value) for value in coordinates)]
        )
        return int.from_bytes(
            hashlib.sha256(message.encode("utf-8")).digest()[:8], "big"
        ) & ((1 << 63) - 1)

    bundle = runtime_seed_bundle(master_seed, cuda_device_indices=(0,))
    assert bundle.model_init == independent("densenet-model-init-v1")
    assert bundle.model_init == 3_170_010_046_903_925_536
    assert bundle.python_runtime == independent("densenet-python-runtime-v1")
    assert bundle.torch_cpu_runtime == independent("densenet-torch-cpu-runtime-v1")
    assert bundle.torch_cuda_runtime == (
        (0, independent("densenet-torch-cuda-runtime-v1", 0)),
    )
    assert loader_worker_base_seed(master_seed, 1) == independent(
        "densenet-loader-worker-base-v1", 1
    )
    assert loader_worker_base_seed(master_seed, 1) != loader_worker_base_seed(
        master_seed, 2
    )


@pytest.mark.parametrize("master_seed", PROJECT_REPRODUCTION_SEEDS)
def test_every_project_seed_replays_all_runtime_domains(master_seed: int) -> None:
    first = runtime_seed_bundle(master_seed, cuda_device_indices=(0, 1))
    second = runtime_seed_bundle(master_seed, cuda_device_indices=(0, 1))
    assert first == second
    values = {
        first.model_init,
        first.python_runtime,
        first.torch_cpu_runtime,
        *(seed for _, seed in first.torch_cuda_runtime),
        loader_worker_base_seed(master_seed, 1),
        loader_worker_base_seed(master_seed, 2),
    }
    assert len(values) == 7


def test_all_project_master_seeds_have_distinct_domain_maps() -> None:
    bundles = [runtime_seed_bundle(seed, cuda_device_indices=(0,)) for seed in PROJECT_REPRODUCTION_SEEDS]
    assert len(set(bundles)) == len(PROJECT_REPRODUCTION_SEEDS)


def test_project_model_seed_is_isolated_replayable_and_domain_separated() -> None:
    ambient = torch.random.get_rng_state().clone()
    first = build_project_seeded_model(PROJECT_REPRODUCTION_SEEDS[0])
    assert torch.equal(torch.random.get_rng_state(), ambient)
    second = build_project_seeded_model(PROJECT_REPRODUCTION_SEEDS[0])
    third = build_project_seeded_model(PROJECT_REPRODUCTION_SEEDS[1])
    assert state_dict_sha256(first) == state_dict_sha256(second)
    assert state_dict_sha256(first) != state_dict_sha256(third)


@pytest.mark.parametrize("master_seed", PROJECT_REPRODUCTION_SEEDS)
def test_every_project_model_seed_is_replayable(master_seed: int) -> None:
    first = build_project_seeded_model(master_seed)
    second = build_project_seeded_model(master_seed)
    assert state_dict_sha256(first) == state_dict_sha256(second)


def test_runtime_rng_initialization_matches_independent_generators() -> None:
    python_state = random.getstate()
    torch_state = torch.random.get_rng_state()
    bundle = runtime_seed_bundle(PROJECT_REPRODUCTION_SEEDS[0])
    try:
        initialize_runtime_rngs(bundle)
        expected_python = random.Random(bundle.python_runtime).getrandbits(64)
        expected_torch_generator = torch.Generator().manual_seed(
            bundle.torch_cpu_runtime
        )
        expected_torch = torch.randint(
            0,
            2**31,
            (8,),
            generator=expected_torch_generator,
            dtype=torch.int64,
        )
        assert random.getrandbits(64) == expected_python
        assert torch.equal(torch.randint(0, 2**31, (8,), dtype=torch.int64), expected_torch)
    finally:
        random.setstate(python_state)
        torch.random.set_rng_state(torch_state)


def test_runtime_rng_bundle_rejects_tampering() -> None:
    valid = runtime_seed_bundle(PROJECT_REPRODUCTION_SEEDS[0])
    tampered = RuntimeSeedBundle(
        master_seed=valid.master_seed,
        model_init=valid.model_init + 1,
        python_runtime=valid.python_runtime,
        torch_cpu_runtime=valid.torch_cpu_runtime,
        torch_cuda_runtime=(),
    )
    with pytest.raises(ValueError, match="does not match"):
        initialize_runtime_rngs(tampered)
    with pytest.raises(ValueError, match="not a preregistered"):
        derive_domain_seed("densenet-model-init-v1", 123)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_cuda_runtime_seed_sets_only_the_explicit_approved_state() -> None:
    original_python = random.getstate()
    original_cpu = torch.random.get_rng_state()
    original_cuda = torch.cuda.get_rng_state_all()
    bundle = runtime_seed_bundle(
        PROJECT_REPRODUCTION_SEEDS[0], cuda_device_indices=(0,)
    )
    try:
        initialize_runtime_rngs(bundle)
        expected = torch.Generator(device="cuda:0").manual_seed(
            bundle.torch_cuda_runtime[0][1]
        )
        assert torch.equal(torch.cuda.get_rng_state(0), expected.get_state())
    finally:
        random.setstate(original_python)
        torch.random.set_rng_state(original_cpu)
        torch.cuda.set_rng_state_all(original_cuda)


def test_optimizer_configuration_covers_all_299_parameters_once() -> None:
    model = build_project_seeded_model(PROJECT_REPRODUCTION_SEEDS[0])
    optimizer = build_phase3_optimizer(model, epoch=150)
    validate_phase3_optimizer(model, optimizer)
    group = optimizer.param_groups[0]
    assert len(group["params"]) == 299
    assert len({id(value) for value in group["params"]}) == 299
    optimized_ids = {id(value) for value in group["params"]}
    named_parameters = dict(model.named_parameters())
    bn_affine_names = [
        name
        for name in named_parameters
        if ("norm" in name and name.endswith((".weight", ".bias")))
    ]
    assert len(bn_affine_names) == 198
    assert all(id(named_parameters[name]) in optimized_ids for name in bn_affine_names)
    assert id(named_parameters["classifier.bias"]) in optimized_ids
    assert group["lr"] == 0.01
    assert group["momentum"] == 0.9
    assert group["dampening"] == 0.0
    assert group["weight_decay"] == 1e-4
    assert group["nesterov"] is True
    assert group["foreach"] is False
    assert group["fused"] is False
    assert group["maximize"] is False
    assert group["differentiable"] is False
    assert set_epoch_learning_rate(optimizer, 225) == 0.001
    assert group["lr"] == 0.001


def test_installed_sgd_matches_independent_two_step_historical_oracle() -> None:
    parameter = torch.nn.Parameter(torch.tensor([1.25, -0.75], dtype=torch.float32))
    optimizer = torch.optim.SGD(
        [parameter],
        lr=0.1,
        momentum=0.9,
        dampening=0.0,
        weight_decay=1e-4,
        nesterov=True,
        maximize=False,
        foreach=False,
        differentiable=False,
        fused=False,
    )
    expected_parameter = parameter.detach().clone()
    expected_buffer: torch.Tensor | None = None
    for raw_gradient in (
        torch.tensor([0.5, -0.25]),
        torch.tensor([-0.125, 0.75]),
    ):
        parameter.grad = raw_gradient.clone()
        decayed_gradient = raw_gradient + 1e-4 * expected_parameter
        if expected_buffer is None:
            expected_buffer = decayed_gradient.clone()
        else:
            expected_buffer = 0.9 * expected_buffer + decayed_gradient
        update = decayed_gradient + 0.9 * expected_buffer
        expected_parameter = expected_parameter - 0.1 * update
        optimizer.step()
        assert torch.equal(parameter.detach(), expected_parameter)
        assert torch.equal(
            optimizer.state[parameter]["momentum_buffer"], expected_buffer
        )


def test_mean_cross_entropy_matches_independent_value_and_gradient() -> None:
    logits = torch.tensor(
        [
            [2.0, -1.0, 0.5, 0.0, -0.5, 1.0, 0.25, -0.25, 0.75, -0.75],
            [-0.5, 0.5, 1.5, -1.0, 0.0, 0.25, -0.25, 0.75, -0.75, 1.0],
        ],
        dtype=torch.float32,
        requires_grad=True,
    )
    targets = torch.tensor([0, 2], dtype=torch.long)
    loss = mean_cross_entropy(logits, targets)
    probabilities = torch.softmax(logits.detach(), dim=1)
    expected_loss = -torch.log(
        probabilities[torch.arange(targets.numel()), targets]
    ).mean()
    expected_gradient = probabilities
    expected_gradient[torch.arange(targets.numel()), targets] -= 1.0
    expected_gradient /= targets.numel()
    loss.backward()
    assert torch.equal(loss.detach(), expected_loss)
    torch.testing.assert_close(logits.grad, expected_gradient, rtol=1e-6, atol=1e-7)


def test_full_model_synthetic_step_tracks_scope_and_historical_update() -> None:
    model = build_project_seeded_model(PROJECT_REPRODUCTION_SEEDS[0])
    with torch.no_grad():
        model.final_norm.bias.fill_(0.25)
        model.classifier.bias.fill_(-0.5)
    optimizer = build_phase3_optimizer(model)
    ledger = SyntheticStepLedger()
    batch = make_synthetic_mechanics_batch(
        batch_size=2, generation_seed=30_001, device="cpu"
    )
    before = {
        "final_norm.bias": model.final_norm.bias.detach().clone(),
        "classifier.bias": model.classifier.bias.detach().clone(),
    }
    loss = synthetic_mechanics_step(
        model=model, optimizer=optimizer, batch=batch, epoch=1, ledger=ledger
    )
    assert torch.isfinite(loss)
    assert ledger.synthetic_optimizer_steps == 1
    assert ledger.formal_optimizer_steps == 0
    assert len(optimizer.state) == 299
    for name, parameter in (
        ("final_norm.bias", model.final_norm.bias),
        ("classifier.bias", model.classifier.bias),
    ):
        raw_gradient = parameter.grad
        assert raw_gradient is not None
        decayed = raw_gradient + 1e-4 * before[name]
        expected = before[name] - 0.1 * (decayed + 0.9 * decayed)
        torch.testing.assert_close(parameter.detach(), expected, rtol=1e-6, atol=1e-7)
        torch.testing.assert_close(
            optimizer.state[parameter]["momentum_buffer"],
            decayed,
            rtol=1e-6,
            atol=1e-7,
        )


def test_stepping_api_rejects_a_forged_nonfactory_batch() -> None:
    model = build_project_seeded_model(PROJECT_REPRODUCTION_SEEDS[0])
    optimizer = build_phase3_optimizer(model)
    forged = SyntheticMechanicsBatch(
        inputs=torch.zeros(2, 3, 32, 32),
        targets=torch.zeros(2, dtype=torch.long),
        generation_seed=1,
        classification="NON-FORMAL-SYNTHETIC-OPTIMIZER-MECHANICS",
        _authorization=object(),
    )
    with pytest.raises(ValueError, match="factory-generated"):
        synthetic_mechanics_step(
            model=model,
            optimizer=optimizer,
            batch=forged,
            epoch=1,
            ledger=SyntheticStepLedger(),
        )
