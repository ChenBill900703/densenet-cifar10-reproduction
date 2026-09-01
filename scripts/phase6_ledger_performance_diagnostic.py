"""Generated-only raw timing diagnostic for the Phase 6 ledger correction."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import tempfile
import time

import densenet_reproduction.phase5 as phase5
from densenet_reproduction.phase5 import AppendOnlyAttemptLedger


def _window(values: list[int], *, first: bool) -> dict[str, int]:
    selected = values[:50] if first else values[-50:]
    ordered = sorted(selected)
    return {
        "maximum_ns": ordered[-1],
        "median_ns": int(statistics.median(ordered)),
        "minimum_ns": ordered[0],
        "samples": len(ordered),
    }


def _measure(calls: int) -> dict[str, object]:
    if not 1 <= calls <= phase5.PHASE5_ACCEPTED_STEPS_PER_SEED:
        raise ValueError("calls must fit one approved seed trajectory.")
    with tempfile.TemporaryDirectory(prefix="densenet-ledger-scaling-") as temporary:
        path = Path(temporary) / "optimizer-attempts.jsonl"
        ledger = AppendOnlyAttemptLedger(path, create=True)
        latencies: list[int] = []
        started = time.perf_counter_ns()
        for offset in range(calls):
            accepted_step = offset + 1
            before = time.perf_counter_ns()
            intent = ledger.append_intent(
                master_seed=phase5.PHASE5_PROJECT_SEEDS[0],
                epoch=offset // 782 + 1,
                batch_index=offset % 782,
                accepted_step=accepted_step,
            )
            ledger.append_completion(intent)
            latencies.append(time.perf_counter_ns() - before)
        append_elapsed = time.perf_counter_ns() - started
        payload = path.read_bytes()
        reopened_started = time.perf_counter_ns()
        reopened = AppendOnlyAttemptLedger(path, create=False)
        reopen_elapsed = time.perf_counter_ns() - reopened_started
        summary = reopened.summary()
        head = (
            reopened.head_sha256
            if hasattr(reopened, "head_sha256")
            else reopened.records[-1]["record_sha256"]
        )
        return {
            "append_elapsed_ns": append_elapsed,
            "calls": calls,
            "file_bytes": len(payload),
            "file_sha256": hashlib.sha256(payload).hexdigest().upper(),
            "first_50_calls": _window(latencies, first=True),
            "head_sha256": head,
            "last_50_calls": _window(latencies, first=False),
            "records": calls * 2,
            "reopen_full_verify_elapsed_ns": reopen_elapsed,
            "summary": {
                "completed_calls": summary.completed_calls,
                "intents": summary.intents,
                "physical_call_lower_bound": summary.physical_call_lower_bound,
                "physical_call_upper_bound": summary.physical_call_upper_bound,
                "unresolved_intents": summary.unresolved_intents,
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", action="append", type=int, required=True)
    arguments = parser.parse_args()
    source = Path(phase5.__file__).resolve(strict=True)
    report = {
        "classification": "PHASE6-LEDGER-PERFORMANCE-GENERATED-ONLY-DIAGNOSTIC",
        "evidence_class": "DERIVED",
        "implementation": {
            "phase5_path": str(source),
            "phase5_sha256": hashlib.sha256(source.read_bytes()).hexdigest().upper(),
        },
        "measurements": [_measure(calls) for calls in arguments.calls],
        "scope": {
            "cifar_access": False,
            "model_constructed": False,
            "optimizer_calls": 0,
            "test_access": False,
        },
        "schema_version": 1,
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
