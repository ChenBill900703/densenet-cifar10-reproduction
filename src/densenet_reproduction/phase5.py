"""Phase 5 freeze-candidate primitives with no model or optimizer execution.

This module is deliberately limited to canonical serialization, immutable
artifact identity, append-only attempt accounting, stage ordering, result
schema validation, and fail-closed launch identity checks.  It never imports
or constructs the DenseNet, CIFAR dataset, loss, or optimizer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Final, Mapping, Sequence


PHASE5_CONFIG_CLASSIFICATION: Final[str] = (
    "PHASE5-FORMAL-CONFIG-CANDIDATE-NOT-FROZEN"
)
PHASE5_EVIDENCE_CLASS: Final[str] = "IMPLEMENTATION-ASSUMPTION"
PHASE5_TARGET_SLUG: Final[str] = (
    "densenet-bc-100-12__cifar10-plus__fp32__b64__e300"
)
PHASE5_DATASET_SHA256: Final[str] = (
    "C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD"
)
FORMAL_EXECUTION_ACCOUNT: Final[str] = os.environ.get(
    "DENSENET_FORMAL_EXECUTION_ACCOUNT", "REDACTED_DOMAIN\\REDACTED_ACCOUNT"
)
FORMAL_EXECUTION_SID: Final[str] = os.environ.get(
    "DENSENET_FORMAL_EXECUTION_SID", "<REDACTED_EXECUTION_SID>"
)
PHASE5_PROJECT_SEEDS: Final[tuple[int, int, int]] = (
    1021082110,
    1747066946,
    869460408,
)
PHASE5_ACCEPTED_STEPS_PER_SEED: Final[int] = 300 * 782
PHASE5_CHECKPOINTS_PER_SEED: Final[int] = 300
PHASE5_STORAGE_HEADROOM_NUMERATOR: Final[int] = 6
PHASE5_STORAGE_HEADROOM_DENOMINATOR: Final[int] = 5

LEDGER_CLASSIFICATION: Final[str] = "FORMAL-OPTIMIZER-ATTEMPT-LEDGER-V1"
LEDGER_HASH_DOMAIN: Final[bytes] = b"DENSENET-FORMAL-ATTEMPT-LEDGER-V1\0"
ZERO_SHA256: Final[str] = "0" * 64

_HEX40 = re.compile(r"^[0-9A-Fa-f]{40}$")
_HEX64 = re.compile(r"^[0-9A-Fa-f]{64}$")
_PORTABLE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def canonical_json_bytes(document: Any) -> bytes:
    """Return the approved sorted/minified/ASCII/LF canonical representation."""

    return (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def sha256_bytes(payload: bytes) -> str:
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes.")
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    _require_regular_file(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _require_regular_file(path: Path) -> None:
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path.")
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular non-symlink file: {path}")


def _plain_int(value: object, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a plain integer.")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in [{minimum}, {maximum}].")
    return value


def _uppercase_sha256(value: object, name: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ValueError(f"{name} must be a 64-character SHA256.")
    if value != value.upper():
        raise ValueError(f"{name} must use uppercase hexadecimal.")
    return value


def read_canonical_json(path: Path) -> Any:
    _require_regular_file(path)
    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Artifact is not valid ASCII JSON.") from error
    if raw != canonical_json_bytes(document):
        raise ValueError("Artifact bytes are not canonical JSON.")
    return document


def validate_formal_config(path: Path) -> dict[str, Any]:
    document = read_canonical_json(path)
    if not isinstance(document, dict):
        raise ValueError("Formal config must be a JSON object.")
    if document != expected_formal_config():
        raise ValueError("Formal config differs from the approved Phase 5 candidate.")
    return document


def expected_formal_config() -> dict[str, Any]:
    """One closed candidate; string decimals avoid binary-float ambiguity."""

    return {
        "checkpoint": {
            "atomic": True,
            "epochs_retained": 300,
            "interrupted_epoch": "rollback-and-rerun",
            "save_every_completed_epoch": True,
        },
        "classification": PHASE5_CONFIG_CLASSIFICATION,
        "dataset": {
            "archive_sha256": PHASE5_DATASET_SHA256,
            "artifact": "cifar-10-binary.tar.gz",
            "classes": 10,
            "test_records": 10000,
            "train_records": 50000,
        },
        "evidence_class": PHASE5_EVIDENCE_CLASS,
        "evaluation": {
            "batch_size": 64,
            "checkpoint_epoch": 300,
            "decode_after_all_training_complete": True,
            "order": "sequential",
            "test_each_seed_once": True,
            "workers": 0,
        },
        "loss": {"kind": "cross_entropy", "reduction": "mean", "source": "raw_logits"},
        "lr": {
            "epoch_1_149": "0.1",
            "epoch_150_224": "0.01",
            "epoch_225_300": "0.001",
            "scheduler_object": False,
        },
        "model": {
            "architecture": "DenseNet-BC",
            "batch_size": 64,
            "bottleneck_multiplier": 4,
            "compression": "0.5-floor",
            "depth": 100,
            "dropout": "0",
            "growth_rate": 12,
            "parameters": 769162,
            "precision": "FP32",
        },
        "optimizer": {
            "dampening": "0",
            "foreach": False,
            "fused": False,
            "momentum": "0.9",
            "nesterov": True,
            "parameter_groups": 1,
            "weight_decay": "0.0001",
            "weight_decay_scope": "all-trainable-parameters",
        },
        "reporting": {
            "aggregation": "arithmetic-mean",
            "individual_runs": True,
            "primary_observation": "integer-incorrect-count-out-of-10000",
            "sample_standard_deviation": "descriptive",
            "selection": "none",
            "success_threshold": None,
        },
        "runtime": {
            "amp": False,
            "compile": False,
            "cudnn_benchmark": False,
            "cudnn_deterministic": True,
            "deterministic_algorithms": True,
            "gradient_accumulation": False,
            "graph": "eager",
            "matmul_precision": "ieee",
            "memory_saving": False,
            "recomputation": False,
            "tf32": False,
        },
        "schema_version": 1,
        "seeds": list(PHASE5_PROJECT_SEEDS),
        "target_slug": PHASE5_TARGET_SLUG,
        "training_data": {
            "augmentation_order": [
                "horizontal-flip-p-0.5",
                "normalized-zero-pad-4",
                "crop-32-offsets-0-through-8",
            ],
            "batches_per_epoch": 782,
            "final_batch_size": 16,
            "normalization_raw255": {
                "mean": ["125.3", "123.0", "113.9"],
                "std": ["63.0", "62.1", "66.7"],
            },
            "shuffle": "densenet-cifar10-loader-v1",
            "workers": 2,
        },
    }


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    path: str
    bytes: int
    sha256: str

    def __post_init__(self) -> None:
        _validate_relative_artifact_path(self.path)
        _plain_int(self.bytes, "artifact bytes", 0, 1 << 63)
        _uppercase_sha256(self.sha256, "artifact sha256")


def _validate_relative_artifact_path(value: str) -> PurePosixPath:
    if (
        not isinstance(value, str)
        or "\\" in value
        or value.startswith("/")
        or "//" in value
        or value.startswith("./")
    ):
        raise ValueError("Artifact path must use portable forward slashes.")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or not candidate.parts:
        raise ValueError("Artifact path must be relative.")
    if any(part in ("", ".", "..") or not _PORTABLE_COMPONENT.fullmatch(part) for part in candidate.parts):
        raise ValueError("Artifact path contains an unsafe component.")
    return candidate


def build_artifact_identities(root: Path) -> tuple[ArtifactIdentity, ...]:
    resolved = root.resolve(strict=True)
    if not resolved.is_dir() or root.is_symlink():
        raise ValueError("Artifact root must be a regular directory.")
    identities: list[ArtifactIdentity] = []
    casefolded: set[str] = set()
    for candidate in sorted(resolved.rglob("*")):
        if candidate.is_symlink():
            raise ValueError(f"Artifact tree contains a symlink: {candidate}")
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(resolved).as_posix()
        folded = relative.casefold()
        if folded in casefolded:
            raise ValueError("Artifact tree contains a case-colliding path.")
        casefolded.add(folded)
        identities.append(
            ArtifactIdentity(relative, candidate.stat().st_size, sha256_file(candidate))
        )
    return tuple(identities)


def verify_artifact_identities(
    root: Path, expected: Sequence[ArtifactIdentity]
) -> None:
    paths = [identity.path for identity in expected]
    if len(paths) != len(set(paths)) or len({path.casefold() for path in paths}) != len(paths):
        raise ValueError("Expected artifact identities contain duplicates/case collisions.")
    observed = build_artifact_identities(root)
    if tuple(expected) != observed:
        raise ValueError("Artifact tree does not exactly match its identity manifest.")


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    intents: int
    completed_calls: int
    unresolved_intents: int
    physical_call_lower_bound: int
    physical_call_upper_bound: int


@dataclass(slots=True)
class _AttemptLedgerState:
    sequence: int = 0
    previous_sha256: str = ZERO_SHA256
    pending: dict[str, dict[str, Any]] = field(default_factory=dict)
    intents: int = 0
    completions: int = 0

    def summary(self) -> AttemptSummary:
        return AttemptSummary(
            intents=self.intents,
            completed_calls=self.completions,
            unresolved_intents=len(self.pending),
            physical_call_lower_bound=self.completions,
            physical_call_upper_bound=self.completions + len(self.pending),
        )


def _ledger_record_hash(body: Mapping[str, Any]) -> str:
    return sha256_bytes(LEDGER_HASH_DOMAIN + canonical_json_bytes(dict(body)))


def _validate_attempt_record(
    raw: Mapping[str, Any], state: _AttemptLedgerState
) -> tuple[dict[str, Any], str, str, str | None]:
    if not isinstance(raw, Mapping):
        raise ValueError("Ledger record must be an object.")
    record = dict(raw)
    record_hash = record.pop("record_sha256", None)
    expected_keys = {
        "accepted_step",
        "batch_index",
        "classification",
        "epoch",
        "event",
        "intent_sha256",
        "master_seed",
        "previous_sha256",
        "sequence",
    }
    if set(record) != expected_keys:
        raise ValueError("Unexpected attempt-ledger record schema.")
    if record["classification"] != LEDGER_CLASSIFICATION:
        raise ValueError("Attempt-ledger classification mismatch.")
    if (
        record["sequence"] != state.sequence + 1
        or record["previous_sha256"] != state.previous_sha256
    ):
        raise ValueError("Attempt-ledger sequence/hash chain is broken.")
    seed = _plain_int(record["master_seed"], "master_seed", 0, (1 << 63) - 1)
    if seed not in PHASE5_PROJECT_SEEDS:
        raise ValueError("Attempt-ledger master seed is not approved.")
    _plain_int(record["epoch"], "epoch", 1, 300)
    _plain_int(record["batch_index"], "batch_index", 0, 781)
    _plain_int(
        record["accepted_step"],
        "accepted_step",
        1,
        PHASE5_ACCEPTED_STEPS_PER_SEED,
    )
    event = record["event"]
    intent_sha = record["intent_sha256"]
    if event == "intent":
        if intent_sha is not None:
            raise ValueError("Intent record cannot reference another intent.")
    elif event == "completion":
        intent_sha = _uppercase_sha256(intent_sha, "intent_sha256")
        if intent_sha not in state.pending:
            raise ValueError("Completion does not reference a pending intent.")
        intent = state.pending[intent_sha]
        for field_name in ("master_seed", "epoch", "batch_index", "accepted_step"):
            if record[field_name] != intent[field_name]:
                raise ValueError("Completion coordinates differ from its intent.")
    else:
        raise ValueError("Attempt-ledger event must be intent or completion.")
    if not isinstance(record_hash, str) or record_hash != _ledger_record_hash(record):
        raise ValueError("Attempt-ledger record hash mismatch.")
    return record, record_hash, event, intent_sha


def _apply_verified_attempt_record(
    state: _AttemptLedgerState,
    record: dict[str, Any],
    record_hash: str,
    event: str,
    intent_sha: str | None,
) -> None:
    if event == "intent":
        state.intents += 1
        state.pending[record_hash] = record
    else:
        if intent_sha is None:  # pragma: no cover - guarded by validation
            raise AssertionError("Validated completion lost its intent identity.")
        state.pending.pop(intent_sha)
        state.completions += 1
    state.sequence += 1
    state.previous_sha256 = record_hash


def _verified_state(
    records: Sequence[Mapping[str, Any]], summary: AttemptSummary
) -> _AttemptLedgerState:
    """Reconstruct cached state only after the public full verifier passes."""

    state = _AttemptLedgerState()
    for raw in records:
        record = dict(raw)
        record_hash = record.pop("record_sha256")
        event = record["event"]
        intent_sha = record["intent_sha256"]
        if event == "intent":
            state.pending[record_hash] = record
        else:
            state.pending.pop(intent_sha)
        state.sequence = record["sequence"]
        state.previous_sha256 = record_hash
    state.intents = summary.intents
    state.completions = summary.completed_calls
    if state.summary() != summary:
        raise AssertionError("Verified attempt-ledger state reconstruction differs.")
    return state


def verify_attempt_records(records: Sequence[Mapping[str, Any]]) -> AttemptSummary:
    state = _AttemptLedgerState()
    for raw in records:
        transition = _validate_attempt_record(raw, state)
        _apply_verified_attempt_record(state, *transition)
    return state.summary()


def _durably_append_attempt_record(path: Path, payload: bytes) -> None:
    with path.open("ab", buffering=0) as stream:
        written = stream.write(payload)
        if written != len(payload):
            raise OSError("Attempt ledger append was short.")
        os.fsync(stream.fileno())


class AppendOnlyAttemptLedger:
    """Create-new JSONL ledger; the public API has no truncate/delete operation."""

    def __init__(self, path: Path, *, create: bool) -> None:
        if not isinstance(path, Path):
            raise TypeError("path must be pathlib.Path.")
        self.path = path
        if create:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        _require_regular_file(path)
        self._records = self._read_records()
        summary = verify_attempt_records(self._records)
        self._state = _verified_state(self._records, summary)
        self._append_failed = False

    def _read_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise ValueError("Attempt ledger has a torn final record.")
        for line in raw.splitlines():
            try:
                value = json.loads(line.decode("ascii"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("Attempt ledger is not canonical JSONL.") from error
            if line + b"\n" != canonical_json_bytes(value):
                raise ValueError("Attempt ledger contains a noncanonical record.")
            records.append(value)
        return records

    @property
    def records(self) -> tuple[dict[str, Any], ...]:
        self._require_usable()
        return tuple(dict(record) for record in self._records)

    @property
    def head_sha256(self) -> str:
        self._require_usable()
        return self._state.previous_sha256

    def _require_usable(self) -> None:
        if self._append_failed:
            raise RuntimeError(
                "Attempt ledger append failed; close and fully verify from disk."
            )

    def _append(self, body: dict[str, Any]) -> str:
        self._require_usable()
        record_hash = _ledger_record_hash(body)
        record = {**body, "record_sha256": record_hash}
        transition = _validate_attempt_record(record, self._state)
        try:
            _durably_append_attempt_record(self.path, canonical_json_bytes(record))
        except BaseException:
            self._append_failed = True
            raise
        try:
            self._records.append(record)
            _apply_verified_attempt_record(self._state, *transition)
        except BaseException:
            self._append_failed = True
            raise
        return record_hash

    def append_intent(
        self, *, master_seed: int, epoch: int, batch_index: int, accepted_step: int
    ) -> str:
        body = self._base_body(
            master_seed=master_seed,
            epoch=epoch,
            batch_index=batch_index,
            accepted_step=accepted_step,
            event="intent",
            intent_sha256=None,
        )
        return self._append(body)

    def append_completion(self, intent_sha256: str) -> str:
        self._require_usable()
        intent_sha256 = _uppercase_sha256(intent_sha256, "intent_sha256")
        if intent_sha256 not in self._state.pending:
            raise ValueError("Completion requires one currently pending intent.")
        intent = self._state.pending[intent_sha256]
        body = self._base_body(
            master_seed=intent["master_seed"],
            epoch=intent["epoch"],
            batch_index=intent["batch_index"],
            accepted_step=intent["accepted_step"],
            event="completion",
            intent_sha256=intent_sha256,
        )
        return self._append(body)

    def _base_body(
        self,
        *,
        master_seed: int,
        epoch: int,
        batch_index: int,
        accepted_step: int,
        event: str,
        intent_sha256: str | None,
    ) -> dict[str, Any]:
        return {
            "accepted_step": accepted_step,
            "batch_index": batch_index,
            "classification": LEDGER_CLASSIFICATION,
            "epoch": epoch,
            "event": event,
            "intent_sha256": intent_sha256,
            "master_seed": master_seed,
            "previous_sha256": (
                self._state.previous_sha256
            ),
            "sequence": self._state.sequence + 1,
        }

    def summary(self) -> AttemptSummary:
        self._require_usable()
        return self._state.summary()


def validate_stage_sequence(events: Sequence[Mapping[str, Any]]) -> None:
    """Reject any test access before all three immutable training completions."""

    expected: list[tuple[str, int]] = []
    expected.extend(("training-complete", seed) for seed in PHASE5_PROJECT_SEEDS)
    expected.extend(("test-complete", seed) for seed in PHASE5_PROJECT_SEEDS)
    observed: list[tuple[str, int]] = []
    for event in events:
        if set(event) != {"event", "master_seed", "checkpoint_epoch", "test_records"}:
            raise ValueError("Unexpected stage-event schema.")
        kind = event["event"]
        seed = event["master_seed"]
        if kind == "training-complete":
            if event["checkpoint_epoch"] != 300 or event["test_records"] != 0:
                raise ValueError("Training completion must be epoch 300 with zero test access.")
        elif kind == "test-complete":
            if event["checkpoint_epoch"] != 300 or event["test_records"] != 10000:
                raise ValueError("Final test completion must cover exactly 10,000 records.")
        else:
            raise ValueError("Unknown stage event.")
        observed.append((kind, seed))
    if observed != expected:
        raise ValueError("Stage events violate fixed train-all-then-test order.")


def validate_seed_result(document: Mapping[str, Any]) -> None:
    expected_keys = {
        "checkpoint_epoch",
        "classification",
        "freeze_manifest_sha256",
        "incorrect_count",
        "master_seed",
        "test_attempts",
        "test_records",
    }
    if set(document) != expected_keys:
        raise ValueError("Unexpected per-seed result schema.")
    if document["classification"] != "FORMAL-FINAL-TEST-RESULT-V1":
        raise ValueError("Per-seed result classification mismatch.")
    if document["master_seed"] not in PHASE5_PROJECT_SEEDS:
        raise ValueError("Per-seed result uses an unapproved seed.")
    if document["checkpoint_epoch"] != 300 or document["test_records"] != 10000:
        raise ValueError("Per-seed result must use epoch 300 and 10,000 records.")
    if document["test_attempts"] != 1:
        raise ValueError("Per-seed result must have exactly one final-test attempt.")
    _plain_int(document["incorrect_count"], "incorrect_count", 0, 10000)
    _uppercase_sha256(document["freeze_manifest_sha256"], "freeze_manifest_sha256")


def expected_aggregate_fields(incorrect_counts: Sequence[int]) -> dict[str, Any]:
    if len(incorrect_counts) != 3:
        raise ValueError("Aggregation requires exactly three incorrect counts.")
    counts = tuple(_plain_int(value, "incorrect_count", 0, 10000) for value in incorrect_counts)
    errors = tuple(Fraction(value, 100) for value in counts)
    mean = sum(errors, start=Fraction()) / 3
    variance = sum(
        ((value - mean) ** 2 for value in errors), start=Fraction()
    ) / 2
    with localcontext() as context:
        context.prec = 50
        sample_sd = (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
    return {
        "incorrect_counts": list(counts),
        "individual_error_percent": [f"{Decimal(value) / Decimal(100):.2f}" for value in counts],
        "mean_error_percent_decimal": format(
            Decimal(mean.numerator) / Decimal(mean.denominator), ".12f"
        ),
        "mean_error_percent_rational": f"{mean.numerator}/{mean.denominator}",
        "sample_standard_deviation_percent": format(sample_sd, ".12f"),
        "sample_standard_deviation_formula": "sqrt(sum((error_i-mean)^2)/(n-1));n=3",
    }


def validate_aggregate_result(document: Mapping[str, Any]) -> None:
    expected_keys = {
        "classification",
        "freeze_manifest_sha256",
        "incorrect_counts",
        "individual_error_percent",
        "mean_error_percent_decimal",
        "mean_error_percent_rational",
        "sample_standard_deviation_formula",
        "sample_standard_deviation_percent",
        "seeds",
        "selection",
    }
    if set(document) != expected_keys:
        raise ValueError("Unexpected aggregate-result schema.")
    if document["classification"] != "FORMAL-AGGREGATE-RESULT-V1":
        raise ValueError("Aggregate-result classification mismatch.")
    if document["seeds"] != list(PHASE5_PROJECT_SEEDS) or document["selection"] != "none":
        raise ValueError("Aggregate result changes seed order or selection policy.")
    _uppercase_sha256(document["freeze_manifest_sha256"], "freeze_manifest_sha256")
    calculated = expected_aggregate_fields(document["incorrect_counts"])
    for key, expected in calculated.items():
        if document[key] != expected:
            raise ValueError(f"Aggregate result field {key} is inconsistent.")


@dataclass(frozen=True, slots=True)
class LaunchIdentity:
    freeze_manifest_sha256: str
    source_commit: str
    config_sha256: str
    dataset_sha256: str
    project_wheel_sha256: str
    python_runtime_sha256: str
    environment_manifest_sha256: str
    execution_account: str
    execution_sid: str
    windows_build: str
    python_build: str
    driver_version: str
    gpu_name: str
    gpu_uuid: str
    compute_capability: str
    deterministic_algorithms: bool
    cudnn_benchmark: bool
    cudnn_deterministic: bool
    convolution_precision: str
    matmul_precision: str
    amp_enabled: bool
    compile_enabled: bool

    def __post_init__(self) -> None:
        for field in (
            "freeze_manifest_sha256",
            "config_sha256",
            "dataset_sha256",
            "project_wheel_sha256",
            "python_runtime_sha256",
            "environment_manifest_sha256",
        ):
            _uppercase_sha256(getattr(self, field), field)
        if not _HEX40.fullmatch(self.source_commit):
            raise ValueError("source_commit must be a full Git SHA1.")
        if (
            not isinstance(self.execution_account, str)
            or "\\" not in self.execution_account
            or not self.execution_account.strip()
        ):
            raise ValueError("execution_account must be a nonempty DOMAIN\\account name.")
        redacted_sid = isinstance(self.execution_sid, str) and bool(
            re.fullmatch(r"<REDACTED_[A-Z0-9_]+_SID>", self.execution_sid)
        )
        if not isinstance(self.execution_sid, str) or not (
            redacted_sid or re.fullmatch(r"S-1(?:-\d+)+", self.execution_sid)
        ):
            raise ValueError("execution_sid must be a Windows SID string.")


def validate_launch_identity(expected: LaunchIdentity, observed: LaunchIdentity) -> None:
    mismatches = [
        field
        for field, expected_value in asdict(expected).items()
        if asdict(observed)[field] != expected_value
    ]
    if mismatches:
        raise RuntimeError("Formal launch identity mismatch: " + ", ".join(mismatches))
    if (
        not observed.deterministic_algorithms
        or observed.cudnn_benchmark
        or not observed.cudnn_deterministic
        or observed.convolution_precision != "ieee"
        or observed.matmul_precision != "ieee"
        or observed.amp_enabled
        or observed.compile_enabled
    ):
        raise RuntimeError("Formal launch policy is not the approved deterministic FP32 policy.")


def required_storage_bytes(checkpoint_bytes: int) -> int:
    size = _plain_int(checkpoint_bytes, "checkpoint_bytes", 1, 1 << 63)
    base = size * PHASE5_CHECKPOINTS_PER_SEED * len(PHASE5_PROJECT_SEEDS)
    numerator = base * PHASE5_STORAGE_HEADROOM_NUMERATOR
    return (numerator + PHASE5_STORAGE_HEADROOM_DENOMINATOR - 1) // (
        PHASE5_STORAGE_HEADROOM_DENOMINATOR
    )


def validate_freeze_manifest(document: Mapping[str, Any]) -> None:
    """Validate the closed top-level freeze-record schema before any launch."""

    expected_keys = {
        "artifacts",
        "classification",
        "config",
        "dataset",
        "environment",
        "evidence_class",
        "policies",
        "schema_version",
        "source",
        "storage",
        "target_slug",
        "tests",
    }
    if set(document) != expected_keys:
        raise ValueError("Unexpected freeze-manifest schema.")
    if document["schema_version"] not in (1, 2):
        raise ValueError("Freeze-manifest schema version mismatch.")
    if document["classification"] != "PHASE5-FREEZE-CANDIDATE-NOT-APPROVED":
        raise ValueError("Freeze-manifest classification mismatch.")
    if document["evidence_class"] != "DERIVED":
        raise ValueError("Freeze-manifest evidence class mismatch.")
    if document["target_slug"] != PHASE5_TARGET_SLUG:
        raise ValueError("Freeze-manifest target slug mismatch.")
    source = document["source"]
    if not isinstance(source, Mapping) or set(source) != {
        "freeze_record_commit",
        "freeze_source_commit",
        "git_bundle_bytes",
        "git_bundle_sha256",
    }:
        raise ValueError("Unexpected freeze-manifest source schema.")
    if not _HEX40.fullmatch(str(source["freeze_source_commit"])):
        raise ValueError("Freeze-source commit is invalid.")
    # The record commit is deliberately null in the candidate bytes because
    # inserting its own hash would be circular. The later decision log binds it.
    if source["freeze_record_commit"] is not None:
        raise ValueError("Freeze-record commit must remain null in its own manifest.")
    _plain_int(source["git_bundle_bytes"], "git_bundle_bytes", 1, 1 << 63)
    _uppercase_sha256(source["git_bundle_sha256"], "git_bundle_sha256")
    config = document["config"]
    if not isinstance(config, Mapping) or set(config) != {"bytes", "path", "sha256"}:
        raise ValueError("Unexpected freeze-manifest config schema.")
    ArtifactIdentity(**dict(config))
    dataset = document["dataset"]
    if not isinstance(dataset, Mapping) or set(dataset) != {"bytes", "path", "sha256"}:
        raise ValueError("Unexpected freeze-manifest dataset schema.")
    dataset_identity = ArtifactIdentity(**dict(dataset))
    if dataset_identity.sha256 != PHASE5_DATASET_SHA256:
        raise ValueError("Freeze-manifest dataset SHA256 is not approved.")
    artifacts = document["artifacts"]
    if not isinstance(artifacts, Mapping) or set(artifacts) != {
        "primary_paper",
        "offline_requirements",
        "project_wheel",
        "python_runtime_archive",
        "python_runtime_manifest",
        "source_lock",
        "wheelhouse_manifest",
    }:
        raise ValueError("Unexpected freeze-manifest artifact schema.")
    for name, value in artifacts.items():
        if not isinstance(value, Mapping):
            raise ValueError(f"Freeze artifact {name} must be an object.")
        ArtifactIdentity(**dict(value))
    environment = document["environment"]
    environment_keys = {
        "compute_capability",
        "driver_version",
        "gpu_name",
        "gpu_uuid",
        "installed_manifest_sha256",
        "python_build",
        "windows_build",
    }
    if document["schema_version"] == 2:
        environment_keys |= {"execution_account", "execution_sid"}
    if not isinstance(environment, Mapping) or set(environment) != environment_keys:
        raise ValueError("Unexpected freeze-manifest environment schema.")
    _uppercase_sha256(
        environment["installed_manifest_sha256"], "installed_manifest_sha256"
    )
    if not all(
        isinstance(environment[key], str) and environment[key]
        for key in environment
        if key != "installed_manifest_sha256"
    ):
        raise ValueError("Freeze-manifest environment identity is incomplete.")
    if document["schema_version"] == 2 and (
        environment["execution_account"] != FORMAL_EXECUTION_ACCOUNT
        or environment["execution_sid"] != FORMAL_EXECUTION_SID
    ):
        raise ValueError("Freeze-manifest execution account/SID is not approved.")
    policies = document["policies"]
    if policies != {
        "attempt_ledger": "append-only-intent-completion-sha256-v1",
        "checkpoint_retention": "all-300-per-seed",
        "final_evaluation": "train-all-three-then-test-once-in-fixed-order",
        "formal_optimizer_steps_at_freeze": 0,
        "run_layout": "runs/formal/<FULL_FREEZE_MANIFEST_SHA256>/seed-<MASTER_SEED>",
    }:
        raise ValueError("Freeze-manifest policies differ from the approved package.")
    storage = document["storage"]
    if not isinstance(storage, Mapping) or set(storage) != {
        "checkpoint_bytes",
        "free_bytes_observed",
        "headroom_percent",
        "required_bytes",
    }:
        raise ValueError("Unexpected freeze-manifest storage schema.")
    checkpoint_bytes = _plain_int(storage["checkpoint_bytes"], "checkpoint_bytes", 1, 1 << 63)
    required = required_storage_bytes(checkpoint_bytes)
    if storage["required_bytes"] != required or storage["headroom_percent"] != 20:
        raise ValueError("Freeze-manifest storage calculation is invalid.")
    free = _plain_int(storage["free_bytes_observed"], "free_bytes_observed", 0, 1 << 63)
    if free < required:
        raise ValueError("Freeze-manifest storage gate is not satisfied.")
    tests = document["tests"]
    if not isinstance(tests, Mapping) or set(tests) != {
        "fresh_offline_passed",
        "formal_optimizer_steps",
        "new_phase5_optimizer_diagnostics",
        "project_passed",
        "source_verifier_passed",
    }:
        raise ValueError("Unexpected freeze-manifest test schema.")
    if tests != {
        "fresh_offline_passed": True,
        "formal_optimizer_steps": 0,
        "new_phase5_optimizer_diagnostics": 0,
        "project_passed": True,
        "source_verifier_passed": True,
    }:
        raise ValueError("Freeze-manifest tests do not satisfy the approved scope.")


@dataclass(frozen=True, slots=True)
class Phase6Authorization:
    freeze_manifest_sha256: str
    phase5_completion_decision_sha256: str
    phase6_entry_decision_sha256: str
    _decision_artifacts_verified: bool = field(
        default=False, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for field in (
            "freeze_manifest_sha256",
            "phase5_completion_decision_sha256",
            "phase6_entry_decision_sha256",
        ):
            _uppercase_sha256(getattr(self, field), field)


def require_phase6_authorization(
    authorization: Phase6Authorization | None,
    *,
    expected_freeze_manifest_sha256: str,
) -> None:
    """The frozen runner cannot mutate until two later approvals exist."""

    expected = _uppercase_sha256(
        expected_freeze_manifest_sha256, "expected_freeze_manifest_sha256"
    )
    if authorization is None:
        raise PermissionError("Phase 6 authorization is absent; mutation is forbidden.")
    if not authorization._decision_artifacts_verified:
        raise PermissionError(
            "Phase 6 decision artifacts have not been hash-verified."
        )
    if authorization.freeze_manifest_sha256 != expected:
        raise PermissionError("Phase 6 authorization names a different freeze manifest.")


def _validate_approved_decision_record(
    document: Any,
    *,
    expected_kind: str,
    expected_freeze_manifest_sha256: str,
) -> None:
    expected_keys = {
        "approval_commit",
        "approved",
        "classification",
        "decision_id",
        "decision_kind",
        "evidence_class",
        "formal_optimizer_steps_at_approval",
        "freeze_manifest_sha256",
        "schema_version",
    }
    if not isinstance(document, Mapping) or set(document) != expected_keys:
        raise ValueError("Unexpected formal decision record schema.")
    if document["schema_version"] != 1:
        raise ValueError("Formal decision record schema version mismatch.")
    if document["classification"] != "FORMAL-GOVERNANCE-DECISION-V1":
        raise ValueError("Formal decision record classification mismatch.")
    if document["evidence_class"] != "IMPLEMENTATION-ASSUMPTION":
        raise ValueError("Formal decision record evidence class mismatch.")
    if document["decision_kind"] != expected_kind:
        raise ValueError("Formal decision record kind mismatch.")
    if document["approved"] is not True:
        raise PermissionError("Formal decision record is not approved.")
    if document["formal_optimizer_steps_at_approval"] != 0:
        raise ValueError("Formal decision record was not approved at step zero.")
    decision_id = document["decision_id"]
    if not isinstance(decision_id, str) or not re.fullmatch(r"D-[0-9]{3}", decision_id):
        raise ValueError("Formal decision ID is invalid.")
    approval_commit = document["approval_commit"]
    if not isinstance(approval_commit, str) or not _HEX40.fullmatch(approval_commit):
        raise ValueError("Formal decision approval commit is invalid.")
    expected = _uppercase_sha256(
        expected_freeze_manifest_sha256, "expected_freeze_manifest_sha256"
    )
    if document["freeze_manifest_sha256"] != expected:
        raise PermissionError("Formal decision record names a different freeze manifest.")


def verify_phase6_decision_artifacts(
    authorization: Phase6Authorization,
    *,
    expected_freeze_manifest_sha256: str,
    phase5_completion_decision_path: Path,
    phase6_entry_decision_path: Path,
) -> None:
    """Bind the runtime capability to two exact canonical approved decisions."""

    expected = _uppercase_sha256(
        expected_freeze_manifest_sha256, "expected_freeze_manifest_sha256"
    )
    if authorization.freeze_manifest_sha256 != expected:
        raise PermissionError("Phase 6 authorization names a different freeze manifest.")
    if phase5_completion_decision_path.resolve(strict=True) == phase6_entry_decision_path.resolve(
        strict=True
    ):
        raise ValueError("Phase 5 and Phase 6 decision artifacts must be distinct files.")
    phase5_document = read_canonical_json(phase5_completion_decision_path)
    phase6_document = read_canonical_json(phase6_entry_decision_path)
    _validate_approved_decision_record(
        phase5_document,
        expected_kind="formal-freeze-completion",
        expected_freeze_manifest_sha256=expected,
    )
    _validate_approved_decision_record(
        phase6_document,
        expected_kind="phase6-entry",
        expected_freeze_manifest_sha256=expected,
    )
    if sha256_file(phase5_completion_decision_path) != authorization.phase5_completion_decision_sha256:
        raise PermissionError("Phase 5 completion decision SHA256 mismatch.")
    if sha256_file(phase6_entry_decision_path) != authorization.phase6_entry_decision_sha256:
        raise PermissionError("Phase 6 entry decision SHA256 mismatch.")
    object.__setattr__(authorization, "_decision_artifacts_verified", True)
