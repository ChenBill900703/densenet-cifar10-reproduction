# Phase 5 Freeze-Candidate Assembly Specification

Status: **IMPLEMENTED AND TECHNICALLY VALIDATED / ACCEPTED AND FROZEN BY D-020**

Evidence class: `IMPLEMENTATION-ASSUMPTION` for approved policies and `DERIVED`
for machine identities. Nothing in this document is a
`FORMAL-REPRODUCTION-RESULT`.

## Fixed candidate identity

- slug: `densenet-bc-100-12__cifar10-plus__fp32__b64__e300`
- config: `config/formal_config.json`
- canonical bytes: ASCII JSON, recursively sorted keys, minified separators,
  terminal LF
- hash display: uppercase SHA256
- project seeds, in order: `1021082110`, `1747066946`, `869460408`
- accepted trajectory steps per completed seed: `300 * 782 = 234,600`
- final test access: only after all three epoch-300 checkpoint manifests are
  hash-verified; each seed once in fixed order

The immutable config bytes retain their historical internal classification
`PHASE5-FORMAL-CONFIG-CANDIDATE-NOT-FROZEN`; D-020 later accepted their exact
SHA256 without rewriting those bytes. The first freeze tag remains preserved.

## Runtime boundaries

The installable `densenet-formal-runner` entry point implements four commands:

- `describe`: Phase 5-safe static description; constructs no model or dataset;
- `train`: later Phase 6 only;
- `evaluate`: later Phase 6 only;
- `aggregate`: later Phase 6 only.

Every mutating/result command requires canonical decision artifacts for both a
later Phase 5 completion decision and later Phase 6 entry decision. It also
recomputes the freeze manifest hash, config/dataset/project-wheel/runtime and
installed-environment identities, verifies the complete live Python runtime,
observes Windows/Python/driver/GPU/precision policy, checks disk headroom, and
fails before model or dataset construction on any mismatch.

## D-022 corrective runtime guards

The corrective candidate adds three pre-execution guards without changing any
scientific setting:

- `--resume-initial-boundary` reopens the fixed seed directory only when the
  append-only ledger and progress log validate, no checkpoint artifact exists,
  and no unresolved intent exists. It deterministically reconstructs the
  initialization boundary and retains all rolled-back physical calls.
- every new or resumed seed validates the complete 300-checkpoint/ledger
  evidence for all earlier seeds and rejects any later seed directory before
  model or dataset construction;
- a raw authorization JSON is not a runtime capability. Closed canonical
  formal-freeze-completion and Phase 6-entry decision files must be distinct,
  approved at formal step zero, bind the same manifest, and match the two exact
  SHA256 values in the authorization JSON before mutation is possible.

These guards were exercised with temporary files, mock factories, and fake
callbacks only. They do not authorize Phase 6 or any CIFAR/model/optimizer
operation.

## Formal training semantics encoded but not executed

The adapter fixes physical batch 64, 782 batches per epoch, workers 2, explicit
epoch sampler/RNG mapping, eager FP32, mean cross-entropy, the approved SGD and
learning-rate function, finite checks, and the sequence:

`zero-grad -> forward -> loss -> backward -> finite-check -> durable intent -> optimizer call -> durable completion -> finite-check`

The attempt ledger is create-new append-only canonical JSONL with a domain-
separated SHA256 chain. Rollback never truncates it. An intent without a
completion yields the conservative physical-call interval `[completed,
completed+unresolved]` and stops automatic resume. Accepted trajectory steps
remain epoch/batch coordinates and are distinct from physical calls.

Each completed epoch publishes one immutable atomic checkpoint and canonical
manifest. The payload includes all model/BN state, all 299 optimizer momentum
buffers, RNG state, exact cursor, attempt bounds, zero test access, and complete
freeze provenance. All 300 checkpoints per seed are retained.

## Final-only evaluation semantics encoded but not executed

Before the test dataset is constructed, the evaluation adapter verifies all
three fixed seed directories and all three epoch-300 checkpoint bytes and
manifests. It then publishes a create-new attempt artifact and fsynced per-batch
progress ledger. An interrupted attempt cannot be silently retried. The result
stores only provenance and the exact integer incorrect count out of 10,000; it
does not store predictions or a best checkpoint.

Aggregation requires all three immutable results in fixed order. It records
all three integer counts, two-decimal individual percentages, exact rational
and 12-place decimal arithmetic mean, and the preregistered sample-standard-
deviation formula. It has no success threshold or selection branch.

## Phase 5-only validation scope

Phase 5 tests may use dictionaries, temporary files, fake callbacks, model
construction without forward, and manually populated zero momentum buffers.
They monkeypatch `SGD.step` to fail in structural checkpoint tests. The only
optimizer calls in a full regression run are the already approved historical
Phase 3/4 generated-only mechanics diagnostics; no new Phase 5 optimizer
diagnostic exists.

The structural checkpoint fixture is explicitly classified
`PHASE5-STRUCTURAL-CHECKPOINT-SIZE-FIXTURE-NO-OPTIMIZER-STEP`. Its current size
and disk calculation are derived evidence to be recorded in the later assembly
report, not a formal checkpoint or runtime performance result.

## Artifact and source identity scheme

The freeze-source candidate commit contains all runtime modules, CLI, config,
schemas, tests, and this specification. The non-editable project wheel and Git
bundle are built from that commit. A later freeze-record commit contains only
machine evidence/manifests and decision documentation. The canonical freeze
manifest leaves its own freeze-record commit field null; the decision log binds
the later record commit, avoiding a circular self-hash.

The Python-runtime artifact includes the interpreter, DLLs, standard-library
sources, and all non-cache runtime files. Generated `__pycache__`, `.pyc`, and
`.pyo` bytecode caches are deliberately excluded from identity and may be
regenerated after extraction; treating those mutable caches as immutable would
make a correct Python startup invalidate its own runtime manifest.

D-020 later approved the Phase 5 completion/freeze package and the first formal
tag. That tag does not authorize training. The later Phase 6 readiness audit
found H-013 through H-015, so a corrective re-freeze and then a separate Phase
6 entry decision are now mandatory.
