from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
import torch

from densenet_reproduction import (
    CheckpointProvenance,
    PROJECT_REPRODUCTION_SEEDS,
    SyntheticStepLedger,
    build_phase3_optimizer,
    build_project_seeded_model,
    load_phase3_checkpoint,
    make_synthetic_mechanics_batch,
    save_phase3_checkpoint,
    state_dict_sha256,
    synthetic_mechanics_step,
)


def _provenance(marker: str = "A") -> CheckpointProvenance:
    return CheckpointProvenance(
        source_commit="5ca9b7261b9cc90faa188bd0460adfb0ab558b6b",
        environment_lock_sha256=marker * 64,
        dataset_sha256="C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD",
        config_sha256="B" * 64,
    )


def _stepped_state(generation_seed: int = 41_001):
    master_seed = PROJECT_REPRODUCTION_SEEDS[0]
    model = build_project_seeded_model(master_seed)
    optimizer = build_phase3_optimizer(model)
    ledger = SyntheticStepLedger()
    batch = make_synthetic_mechanics_batch(
        batch_size=2, generation_seed=generation_seed, device="cpu"
    )
    synthetic_mechanics_step(
        model=model, optimizer=optimizer, batch=batch, epoch=1, ledger=ledger
    )
    return master_seed, model, optimizer, ledger


def _assert_optimizer_states_equal(
    first: torch.optim.Optimizer, second: torch.optim.Optimizer
) -> None:
    first_state = first.state_dict()
    second_state = second.state_dict()
    assert first_state["param_groups"] == second_state["param_groups"]
    assert set(first_state["state"]) == set(second_state["state"])
    for parameter_id, values in first_state["state"].items():
        assert set(values) == set(second_state["state"][parameter_id])
        for name, value in values.items():
            other = second_state["state"][parameter_id][name]
            if isinstance(value, torch.Tensor):
                assert torch.equal(value.cpu(), other.cpu())
            else:
                assert value == other


def _rewrite_manifest_for_payload(checkpoint: Path) -> None:
    payload_bytes = checkpoint.read_bytes()
    manifest_path = checkpoint.with_name(f"{checkpoint.name}.manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["bytes"] = len(payload_bytes)
    manifest["sha256"] = hashlib.sha256(payload_bytes).hexdigest().upper()
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _rewrite_checkpoint_payload(checkpoint: Path, payload: dict[str, object]) -> None:
    torch.save(payload, checkpoint)
    _rewrite_manifest_for_payload(checkpoint)


def test_checkpoint_round_trip_restores_every_state_and_rng(tmp_path: Path) -> None:
    master_seed, model, optimizer, ledger = _stepped_state()
    checkpoint = tmp_path / "epoch_001.pt"
    cpu_rng_at_save = torch.random.get_rng_state().clone()
    manifest = save_phase3_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=tmp_path,
        model=model,
        optimizer=optimizer,
        ledger=ledger,
        completed_epoch=1,
        master_seed=master_seed,
        provenance=_provenance(),
    )
    saved_model_hash = state_dict_sha256(model)
    restored_model = build_project_seeded_model(master_seed)
    restored_optimizer = build_phase3_optimizer(restored_model)
    torch.manual_seed(999)
    result = load_phase3_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=tmp_path,
        model=restored_model,
        optimizer=restored_optimizer,
        expected_master_seed=master_seed,
        expected_provenance=_provenance(),
    )
    assert result.completed_epoch == 1
    assert result.next_epoch == 2
    assert result.synthetic_optimizer_steps == 1
    assert result.formal_optimizer_steps == 0
    assert result.checkpoint_sha256 == manifest["sha256"]
    assert state_dict_sha256(restored_model) == saved_model_hash
    _assert_optimizer_states_equal(optimizer, restored_optimizer)
    assert torch.equal(torch.random.get_rng_state(), cpu_rng_at_save)


def test_checkpoint_resume_matches_uninterrupted_synthetic_trajectory(
    tmp_path: Path,
) -> None:
    master_seed, continuous_model, continuous_optimizer, ledger = _stepped_state(
        42_001
    )
    checkpoint = tmp_path / "epoch_001.pt"
    save_phase3_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=tmp_path,
        model=continuous_model,
        optimizer=continuous_optimizer,
        ledger=ledger,
        completed_epoch=1,
        master_seed=master_seed,
        provenance=_provenance(),
    )
    next_batch = make_synthetic_mechanics_batch(
        batch_size=2, generation_seed=42_002, device="cpu"
    )
    continuous_loss = synthetic_mechanics_step(
        model=continuous_model,
        optimizer=continuous_optimizer,
        batch=next_batch,
        epoch=2,
        ledger=ledger,
    )

    resumed_model = build_project_seeded_model(master_seed)
    resumed_optimizer = build_phase3_optimizer(resumed_model)
    result = load_phase3_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=tmp_path,
        model=resumed_model,
        optimizer=resumed_optimizer,
        expected_master_seed=master_seed,
        expected_provenance=_provenance(),
    )
    resumed_ledger = SyntheticStepLedger(result.synthetic_optimizer_steps)
    resumed_loss = synthetic_mechanics_step(
        model=resumed_model,
        optimizer=resumed_optimizer,
        batch=next_batch,
        epoch=result.next_epoch,
        ledger=resumed_ledger,
    )
    assert torch.equal(continuous_loss, resumed_loss)
    assert state_dict_sha256(continuous_model) == state_dict_sha256(resumed_model)
    _assert_optimizer_states_equal(continuous_optimizer, resumed_optimizer)
    assert ledger.synthetic_optimizer_steps == resumed_ledger.synthetic_optimizer_steps == 2
    assert ledger.formal_optimizer_steps == resumed_ledger.formal_optimizer_steps == 0


def test_checkpoint_load_fails_before_model_mutation_on_provenance_mismatch(
    tmp_path: Path,
) -> None:
    master_seed, model, optimizer, ledger = _stepped_state(43_001)
    checkpoint = tmp_path / "epoch_001.pt"
    save_phase3_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=tmp_path,
        model=model,
        optimizer=optimizer,
        ledger=ledger,
        completed_epoch=1,
        master_seed=master_seed,
        provenance=_provenance(),
    )
    target_model = build_project_seeded_model(master_seed)
    target_optimizer = build_phase3_optimizer(target_model)
    before = state_dict_sha256(target_model)
    with pytest.raises(ValueError, match="provenance mismatch"):
        load_phase3_checkpoint(
            checkpoint_path=checkpoint,
            allowed_root=tmp_path,
            model=target_model,
            optimizer=target_optimizer,
            expected_master_seed=master_seed,
            expected_provenance=_provenance("C"),
        )
    assert state_dict_sha256(target_model) == before
    assert target_optimizer.state == {}


@pytest.mark.parametrize(
    "field_name",
    ["source_commit", "environment_lock_sha256", "dataset_sha256", "config_sha256"],
)
def test_every_provenance_domain_mismatch_fails_closed(
    tmp_path: Path, field_name: str
) -> None:
    master_seed, model, optimizer, ledger = _stepped_state(43_100)
    checkpoint = tmp_path / f"{field_name}.pt"
    provenance = _provenance()
    save_phase3_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=tmp_path,
        model=model,
        optimizer=optimizer,
        ledger=ledger,
        completed_epoch=1,
        master_seed=master_seed,
        provenance=provenance,
    )
    replacement = "C" * (40 if field_name == "source_commit" else 64)
    expected = replace(provenance, **{field_name: replacement})
    target_model = build_project_seeded_model(master_seed)
    target_optimizer = build_phase3_optimizer(target_model)
    before = state_dict_sha256(target_model)
    with pytest.raises(ValueError, match="provenance mismatch"):
        load_phase3_checkpoint(
            checkpoint_path=checkpoint,
            allowed_root=tmp_path,
            model=target_model,
            optimizer=target_optimizer,
            expected_master_seed=master_seed,
            expected_provenance=expected,
        )
    assert state_dict_sha256(target_model) == before
    assert target_optimizer.state == {}


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_key", "payload schema"),
        ("extra_key", "payload schema"),
        ("wrong_seed", "master seed"),
        ("wrong_policy", "policy identifiers"),
        ("wrong_model_metadata", "model metadata"),
        ("wrong_model_tensor", "Model state metadata"),
        ("missing_model_tensor", "state names/order"),
        ("extra_model_tensor", "state names/order"),
        ("wrong_optimizer_tensor", "Momentum buffer tensor metadata"),
        ("extra_optimizer_group_key", "parameter-group schema"),
        ("wrong_python_rng", "Python RNG state is invalid"),
        ("wrong_cpu_rng", "PyTorch CPU RNG state is invalid"),
        ("nonzero_formal_steps", "Formal optimizer steps"),
    ],
)
def test_hash_consistent_payload_tampering_fails_before_state_mutation(
    tmp_path: Path, mutation: str, message: str
) -> None:
    master_seed, model, optimizer, ledger = _stepped_state(43_200)
    checkpoint = tmp_path / f"{mutation}.pt"
    save_phase3_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=tmp_path,
        model=model,
        optimizer=optimizer,
        ledger=ledger,
        completed_epoch=1,
        master_seed=master_seed,
        provenance=_provenance(),
    )
    payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if mutation == "missing_key":
        del payload["classification"]
    elif mutation == "extra_key":
        payload["unexpected"] = None
    elif mutation == "wrong_seed":
        payload["master_seed"] = PROJECT_REPRODUCTION_SEEDS[1]
    elif mutation == "wrong_policy":
        payload["policy_ids"]["optimizer"] = "tampered"
    elif mutation == "wrong_model_metadata":
        payload["model_metadata"]["stem.weight"]["shape"] = [1]
    elif mutation == "wrong_model_tensor":
        payload["model_state"]["stem.weight"] = torch.zeros(1)
    elif mutation == "missing_model_tensor":
        del payload["model_state"]["stem.weight"]
    elif mutation == "extra_model_tensor":
        payload["model_state"]["unexpected"] = torch.zeros(1)
    elif mutation == "wrong_optimizer_tensor":
        payload["optimizer_state"]["state"][0]["momentum_buffer"] = torch.zeros(1)
    elif mutation == "extra_optimizer_group_key":
        payload["optimizer_state"]["param_groups"][0]["unexpected"] = False
    elif mutation == "wrong_python_rng":
        payload["rng_state"]["python"] = (999, (), None)
    elif mutation == "wrong_cpu_rng":
        payload["rng_state"]["torch_cpu"] = torch.zeros(1, dtype=torch.uint8)
    elif mutation == "nonzero_formal_steps":
        payload["formal_optimizer_steps"] = 1
    else:  # pragma: no cover - the parametrization is closed above
        raise AssertionError(mutation)
    _rewrite_checkpoint_payload(checkpoint, payload)

    target_model = build_project_seeded_model(master_seed)
    target_optimizer = build_phase3_optimizer(target_model)
    before = state_dict_sha256(target_model)
    with pytest.raises(ValueError, match=message):
        load_phase3_checkpoint(
            checkpoint_path=checkpoint,
            allowed_root=tmp_path,
            model=target_model,
            optimizer=target_optimizer,
            expected_master_seed=master_seed,
            expected_provenance=_provenance(),
        )
    assert state_dict_sha256(target_model) == before
    assert target_optimizer.state == {}


def test_checkpoint_corruption_and_missing_manifest_fail_closed(tmp_path: Path) -> None:
    master_seed, model, optimizer, ledger = _stepped_state(44_001)
    checkpoint = tmp_path / "epoch_001.pt"
    save_phase3_checkpoint(
        checkpoint_path=checkpoint,
        allowed_root=tmp_path,
        model=model,
        optimizer=optimizer,
        ledger=ledger,
        completed_epoch=1,
        master_seed=master_seed,
        provenance=_provenance(),
    )
    payload = bytearray(checkpoint.read_bytes())
    payload[len(payload) // 2] ^= 0x01
    checkpoint.write_bytes(payload)
    with pytest.raises(ValueError, match="SHA256"):
        load_phase3_checkpoint(
            checkpoint_path=checkpoint,
            allowed_root=tmp_path,
            model=build_project_seeded_model(master_seed),
            optimizer=build_phase3_optimizer(build_project_seeded_model(master_seed)),
            expected_master_seed=master_seed,
            expected_provenance=_provenance(),
        )

    missing_manifest_checkpoint = tmp_path / "missing.pt"
    missing_manifest_checkpoint.write_bytes(b"not a checkpoint")
    with pytest.raises(ValueError, match="regular non-symlink"):
        load_phase3_checkpoint(
            checkpoint_path=missing_manifest_checkpoint,
            allowed_root=tmp_path,
            model=build_project_seeded_model(master_seed),
            optimizer=build_phase3_optimizer(build_project_seeded_model(master_seed)),
            expected_master_seed=master_seed,
            expected_provenance=_provenance(),
        )


def test_checkpoint_is_immutable_and_cannot_escape_allowed_root(tmp_path: Path) -> None:
    master_seed, model, optimizer, ledger = _stepped_state(45_001)
    checkpoint = tmp_path / "epoch_001.pt"
    arguments = dict(
        checkpoint_path=checkpoint,
        allowed_root=tmp_path,
        model=model,
        optimizer=optimizer,
        ledger=ledger,
        completed_epoch=1,
        master_seed=master_seed,
        provenance=_provenance(),
    )
    save_phase3_checkpoint(**arguments)
    with pytest.raises(FileExistsError, match="already exists"):
        save_phase3_checkpoint(**arguments)
    with pytest.raises(ValueError, match="escapes"):
        save_phase3_checkpoint(
            **{**arguments, "checkpoint_path": tmp_path.parent / "escape.pt"}
        )


def test_checkpoint_provenance_requires_exact_hash_shapes() -> None:
    with pytest.raises(ValueError, match="full 40-character"):
        CheckpointProvenance(
            source_commit="short",
            environment_lock_sha256="A" * 64,
            dataset_sha256="B" * 64,
            config_sha256="C" * 64,
        )
    with pytest.raises(ValueError, match="environment_lock_sha256"):
        CheckpointProvenance(
            source_commit="a" * 40,
            environment_lock_sha256="not-a-hash",
            dataset_sha256="B" * 64,
            config_sha256="C" * 64,
        )
