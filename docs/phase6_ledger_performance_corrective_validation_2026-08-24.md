# Phase 6 Ledger-Performance Corrective Technical Validation

Status: **TECHNICALLY VALIDATED / CORRECTIVE-FREEZE COMPLETION DECISION PENDING / NEW PHASE 6 EXECUTION FORBIDDEN**

Date: **2026-08-24**

This record is `DERIVED` evidence under D-042. It is not a formal reproduction
result, does not create a tag, and does not authorize a new CIFAR model
forward, loss, backward, optimizer call, training run, test access,
evaluation, prediction, accuracy, or aggregation. The old incomplete run is
historical formal-attempt evidence; the new candidate has zero formal
optimizer calls.

## Candidate identities

| Item | Identity |
|---|---|
| Corrective freeze-source commit | `863375d4082abaa2a7f6580e4f90c3ec114cbce3` |
| Schema-v2 manifest candidate | SHA256 `6CC22F7D918DF1689C4E14A33E8BB4FDAF502EF51149AF1E6537D2618547EC26` |
| Deterministic project wheel | 58,472 bytes; SHA256 `D31FE8A0DFBDBF4B4100C28E587DDDA98A13EE63219B373143DF41C01F8CE859` |
| Installed environment manifest | SHA256 `1E0D0EA18AE43BCBEDA2962EB363C7D8CE7FBB8B2B03000D33A8BEA130A7C953` |
| Offline requirements | SHA256 `7868BEFE59FF88707788C2B2C21AB1D26F51383ED00C3D5D3995F4E673DC9DD6` |
| Complete source bundle | 4,604,199 bytes; SHA256 `C5C9C75921493188192C18610DE11449EA5178B69E5E6319EB3AEAC2F680BEAF` |
| Generated scaling report | SHA256 `1A34BDD6677043DD68F8E4A49A42DC8EA554D1E06DC65015651DAF8EF4CA5878` |
| Machine report | SHA256 `5BA5972212E1A55BC1BEBC28CB9AEAA69CC7235F46ECB9B1D9F51B717C137286` |

The later commit containing this validation and the candidate evidence is the
non-circular freeze-record candidate. The manifest and machine report retain
`freeze_record_commit: null`.

## Controlled stop and immutable old run

D-043 stopped only the verified project process tree. The cooperative
`CTRL_BREAK` attempt was unavailable with `WinError 87`; the verified workers,
trainer, console helper, and wrapper were then terminated child-first. No
project Python/GPU process remained.

The permanent stop classification is exactly
`HUMAN-DEADLINE-PERFORMANCE-CORRECTIVE-ABANDONMENT`. The old namespace is
incomplete, abandoned, immutable, and non-resumable:

- 24,421 intents and 24,421 completions; unresolved intents 0;
- exact physical interval `[24421,24421]`;
- ledger head `F7DEC0A937D25F784E038569BBC20AD9496221D53BC8805189AD695034637909`;
- 30 checkpoint/manifest pairs, with `epoch-030.pt` the latest;
- 62 files and no temporary, later-seed, test, or evaluation artifact.

The corrected full verifier reopened all 48,842 old records in 0.7542773 s,
reproduced the same counts/head, and left the 18,896,262-byte ledger SHA256
`59D4B7C11D50F7339C172F9600819E3608B0AA394BFEE83428AF056149974451`
unchanged. Final size/SHA256 enumeration also matched all 62 D-043 artifacts.
D-028 still contains exactly its two zero-byte SHA256-empty files. All three
older annotated tags remain at their accepted objects and peeled targets.

## H-020 correction

The source allowlist contains only:

- `src/densenet_reproduction/phase5.py`;
- `src/densenet_reproduction/formal_training.py`;
- `tests/test_ledger_performance_corrective.py`;
- `scripts/phase6_ledger_performance_diagnostic.py`.

On open/reopen, an existing ledger still receives one complete unchanged
`verify_attempt_records` audit before state is reconstructed. A new record is
then checked against the verified in-memory state, written as the same
canonical JSON/hash-domain/sequence, appended and fsynced, and only after that
durable success reflected in memory. Public full-ledger audit remains
available. Torn lines, wrong sequence/hash, missing/cross/duplicate
completion, short/failed write, failed fsync, and poisoned post-failure state
all fail closed; no repair, truncate, rewrite, or completion synthesis exists.

Differential/property/mutation/crash/reopen tests confirm identical record
bytes, hashes, pending state, physical bounds, and rejection decisions. The
500- and 2,000-call generated ledgers were also byte-identical to the old
implementation. No scientific model, data, augmentation, RNG, loss, SGD, LR,
checkpoint, evaluation, or reporting rule changed, and corrected source is
forbidden from loading the old checkpoint.

## Raw scaling and deadline disposition

Fresh-wheel generated-only measurements produced:

| Calls | Append elapsed | Last-50 median/call | Full reopen audit |
|---:|---:|---:|---:|
| 500 | 1.5214824 s | 2.8919 ms | 0.0160652 s |
| 2,000 | 6.1024451 s | 3.1099 ms | 0.0665728 s |
| 8,000 | 10.1052038 s | 1.2546 ms | 0.2557590 s |
| 20,000 | 30.5970268 s | 0.9334 ms | 0.6368625 s |

The hot-path last-50 latency no longer grows with the ledger length; the
required full reopen audit remains linear and occurs at open/recovery, not on
every append.

For the deadline disposition, subtracting the accepted H-020 slopes from the
old observed epoch intervals yields 363.662-375.002 s/epoch intercepts. Adding
the observed corrected last-50 range for 782 calls gives a derived
364.3919188-377.4339418 s/epoch projection. Across 900 training epochs this is
91.0979797-94.35848545 hours, or about 3.80-3.93 days.

Disposition: **`OBSERVED-WEEK-FEASIBLE`**.

This is not a seven-day guarantee. Approval/relaunch latency, final
evaluation, host contention, interruption, and failure recovery are not
modeled. No automatic headroom threshold or protocol workaround was applied.

## Rebuild and verification

- Project strict suite: **191/191**, warnings as errors.
- Fresh offline non-editable formal-wheel strict suite: **191/191**, warnings
  as errors. An initial 190/191 invocation omitted the required existing
  `DENSENET_PACKAGE_MODE=formal-wheel` test selector; the failure itself showed
  site-packages loading. The correctly declared full rerun passed 191/191.
- Two source-date-epoch wheel builds were byte-identical.
- Fresh reconstruction used only `--no-index --require-hashes` artifacts.
- The fresh environment contains 21 distributions and 23,822 RECORD files;
  its pre/post-test manifests are bit-exact.
- Source verification passed 19/19 files and 5/5 complete repositories.
- Project and fresh environments each verified 20/20 wheels, 8,264/8,264
  runtime files, paper, dataset, config, source lock, project wheel, and full
  source bundle against the schema-v2 manifest.
- Exact-account preflight passed for `<REDACTED_EXECUTION_ACCOUNT>`, the approved
  SID, RTX 3070 Ti identity, deterministic IEEE FP32, AMP off, and compile
  off, without constructing a dataset, model, optimizer, or formal root.
- A separate exact-account training-only check verified the prepared manifest
  and five training batch size/SHA256 identities; `test_batch.bin` was not
  accessed.
- Storage passed: 7,164,705,960 required bytes versus 40,998,916,096 observed
  free bytes.

## Remaining gates

Technical assembly is complete, but the candidate is not frozen. A separate
human-approved corrective-freeze completion package is required before the
proposed annotated tag
`formal-freeze-densenet-bc100-12-cifar10plus-ledger-performance-corrected-2026-08-24`
may be created. A further Phase 6 entry package bound to the new tag,
manifest, wheel, environment, dataset, stop report, and canonical decisions
is required before a fresh namespace may be created and all three seeds are
rerun from epoch 1.
