from __future__ import annotations

import hashlib
import inspect
import random
from pathlib import Path

import pytest

import densenet_reproduction.phase5 as phase5
from densenet_reproduction.phase5 import (
    AppendOnlyAttemptLedger,
    PHASE5_PROJECT_SEEDS,
    verify_attempt_records,
)


def _new_ledger(tmp_path: Path, name: str = "ledger.jsonl") -> AppendOnlyAttemptLedger:
    return AppendOnlyAttemptLedger(tmp_path / name, create=True)


def test_incremental_writer_preserves_frozen_record_bytes(tmp_path: Path) -> None:
    ledger = _new_ledger(tmp_path)
    intent = ledger.append_intent(
        master_seed=1021082110, epoch=1, batch_index=0, accepted_step=1
    )
    completion = ledger.append_completion(intent)
    assert intent == "9BEE03747611AF6C0EFDA7D635B3E6754671A0D58387EDE67D45BE369483EDD3"
    assert completion == "09DE914380CC780FF2861532D5B6FD8B3E80CFD451D7C0920395AC711AE15B39"
    frozen_bytes = ledger.path.read_bytes()
    assert len(frozen_bytes) == 754
    assert hashlib.sha256(frozen_bytes).hexdigest().upper() == (
        "6EF04D188F2208D920E6B152F13F30F26BFDD2C5ACBCE251DA7677213B05813D"
    )


def test_incremental_summary_matches_full_verifier_for_generated_sequences(
    tmp_path: Path,
) -> None:
    ledger = _new_ledger(tmp_path)
    rng = random.Random(20260824)
    pending: list[str] = []
    next_coordinate = 1
    for _ in range(240):
        if pending and rng.random() < 0.48:
            ledger.append_completion(pending.pop(rng.randrange(len(pending))))
        else:
            coordinate = next_coordinate
            next_coordinate += 1
            pending.append(
                ledger.append_intent(
                    master_seed=PHASE5_PROJECT_SEEDS[0],
                    epoch=(coordinate - 1) // 782 + 1,
                    batch_index=(coordinate - 1) % 782,
                    accepted_step=coordinate,
                )
            )
        assert ledger.summary() == verify_attempt_records(ledger.records)
        assert ledger.head_sha256 == ledger.records[-1]["record_sha256"]
    while pending:
        ledger.append_completion(pending.pop())
    reopened = AppendOnlyAttemptLedger(ledger.path, create=False)
    assert reopened.summary() == ledger.summary()
    assert reopened.head_sha256 == ledger.head_sha256


def test_existing_ledger_runs_public_full_verifier_once_then_appends_incrementally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _new_ledger(tmp_path)
    intent = ledger.append_intent(
        master_seed=1021082110, epoch=1, batch_index=0, accepted_step=1
    )
    ledger.append_completion(intent)
    original = phase5.verify_attempt_records
    calls = 0

    def counted(records: object) -> phase5.AttemptSummary:
        nonlocal calls
        calls += 1
        return original(records)  # type: ignore[arg-type]

    monkeypatch.setattr(phase5, "verify_attempt_records", counted)
    reopened = AppendOnlyAttemptLedger(ledger.path, create=False)
    assert calls == 1

    def forbidden(records: object) -> phase5.AttemptSummary:
        raise AssertionError("append path invoked the full-history verifier")

    monkeypatch.setattr(phase5, "verify_attempt_records", forbidden)
    second = reopened.append_intent(
        master_seed=1021082110, epoch=1, batch_index=1, accepted_step=2
    )
    reopened.append_completion(second)
    assert reopened.summary().completed_calls == 2


@pytest.mark.parametrize(
    "mutation",
    [
        {"classification": "wrong"},
        {"sequence": 2},
        {"previous_sha256": "A" * 64},
        {"master_seed": 1},
        {"epoch": 0},
        {"batch_index": 782},
        {"accepted_step": 0},
        {"event": "wrong"},
        {"intent_sha256": "A" * 64},
    ],
)
def test_incremental_rejection_matches_full_verifier(
    tmp_path: Path, mutation: dict[str, object]
) -> None:
    ledger = _new_ledger(tmp_path)
    body: dict[str, object] = {
        "accepted_step": 1,
        "batch_index": 0,
        "classification": phase5.LEDGER_CLASSIFICATION,
        "epoch": 1,
        "event": "intent",
        "intent_sha256": None,
        "master_seed": 1021082110,
        "previous_sha256": phase5.ZERO_SHA256,
        "sequence": 1,
    }
    body.update(mutation)
    record = {**body, "record_sha256": phase5._ledger_record_hash(body)}
    with pytest.raises(ValueError) as full_error:
        verify_attempt_records([record])
    with pytest.raises(ValueError) as incremental_error:
        ledger._append(body)  # noqa: SLF001 - differential test of frozen boundary
    assert str(incremental_error.value) == str(full_error.value)
    assert ledger.path.read_bytes() == b""


def test_fsync_failure_poisoned_object_requires_full_reopen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _new_ledger(tmp_path)
    original_fsync = phase5.os.fsync

    def fail_fsync(descriptor: int) -> None:
        raise OSError("generated fsync failure")

    monkeypatch.setattr(phase5.os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="generated fsync failure"):
        ledger.append_intent(
            master_seed=1021082110, epoch=1, batch_index=0, accepted_step=1
        )
    with pytest.raises(RuntimeError, match="fully verify"):
        ledger.summary()
    monkeypatch.setattr(phase5.os, "fsync", original_fsync)
    reopened = AppendOnlyAttemptLedger(ledger.path, create=False)
    assert reopened.summary().unresolved_intents == 1


def test_short_write_fails_before_fsync(monkeypatch: pytest.MonkeyPatch) -> None:
    fsync_called = False

    class ShortStream:
        def __enter__(self) -> ShortStream:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def write(self, payload: bytes) -> int:
            return len(payload) - 1

        def fileno(self) -> int:
            return 1

    def short_open(*args: object, **kwargs: object) -> ShortStream:
        return ShortStream()

    def observed_fsync(descriptor: int) -> None:
        nonlocal fsync_called
        fsync_called = True

    monkeypatch.setattr(Path, "open", short_open)
    monkeypatch.setattr(phase5.os, "fsync", observed_fsync)
    with pytest.raises(OSError, match="short"):
        phase5._durably_append_attempt_record(Path("unused"), b"record\n")
    assert not fsync_called


def test_crash_after_durable_write_recovers_only_by_full_reopen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _new_ledger(tmp_path)
    original_apply = phase5._apply_verified_attempt_record

    def generated_crash(*args: object) -> None:
        raise RuntimeError("generated post-durable crash")

    monkeypatch.setattr(phase5, "_apply_verified_attempt_record", generated_crash)
    with pytest.raises(RuntimeError, match="generated post-durable crash"):
        ledger.append_intent(
            master_seed=1021082110, epoch=1, batch_index=0, accepted_step=1
        )
    with pytest.raises(RuntimeError, match="fully verify"):
        ledger.records
    monkeypatch.setattr(phase5, "_apply_verified_attempt_record", original_apply)
    reopened = AppendOnlyAttemptLedger(ledger.path, create=False)
    assert reopened.summary().unresolved_intents == 1


def test_formal_hot_path_does_not_copy_or_full_verify_history() -> None:
    append_source = inspect.getsource(AppendOnlyAttemptLedger._append)
    completion_source = inspect.getsource(AppendOnlyAttemptLedger.append_completion)
    training_source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "densenet_reproduction"
        / "formal_training.py"
    ).read_text(encoding="utf-8")
    assert "verify_attempt_records" not in append_source
    assert "self._records" not in completion_source
    assert 'ledger.records[-1]["record_sha256"]' not in training_source
