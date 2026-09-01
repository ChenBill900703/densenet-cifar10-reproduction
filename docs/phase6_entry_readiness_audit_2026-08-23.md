# Phase 6 Entry Readiness Audit

Status: **BLOCKED - CORRECTIVE RE-FREEZE REQUIRED BEFORE PHASE 6 ENTRY**

Date: **2026-08-23**

This is a read-only/static audit of the formally frozen runner at freeze-source
`5d5d6d89cde00134776a59924896758f30816281`. It constructed no DenseNet or
CIFAR dataset, performed no loss/backward/optimizer operation, decoded no test
record, and left formal optimizer steps at **0**. It is not a
`FORMAL-REPRODUCTION-RESULT`.

## Outcome

The frozen identities and Phase 5 evidence still hash correctly, but Phase 6
must not be entered yet. Three fail-closed obligations are not fully enforced
by the frozen CLI. Because they affect recovery, run ordering, and authorization
identity, they are `BLOCKER`s rather than documentation-only observations.

## H-013 - No legal epoch-1 rollback path

`formal_cli.py` creates the fixed seed directory only when no resume checkpoint
is supplied. A retry after an epoch-1 interruption has no epoch checkpoint to
name, but the fixed directory already exists, so create-new fails. The lower
training API can reopen an existing ledger, yet the frozen CLI exposes no
authorized initial-boundary resume mode. Therefore A-012/H-006's stated
interrupted-epoch rollback-and-rerun rule is incomplete for the first epoch.

Required correction: add an explicit initial-boundary resume mode that may
reopen exactly the existing seed directory only when no completed checkpoint
exists, the append-only ledger/progress artifacts validate, and no unresolved
optimizer intent exists. It must deterministically rebuild initialization and
rerun epoch 1 while retaining every prior physical call in the ledger.

## H-014 - Formal seed training order is not enforced

The frozen CLI accepts any of the three project seeds, and
`require_create_new_formal_run_root` creates that seed directory without
verifying completion of earlier seeds. A static no-model diagnostic created
`seed-1747066946` before `seed-1021082110`. Evaluation order is guarded later,
but A-018/M-007 requires the formal training trajectories themselves to finish
in the fixed seed order.

Required correction: before creating or resuming a seed, verify that every
earlier frozen seed has a valid immutable epoch-300 checkpoint/manifest and
that no later seed has begun. This check must occur before model or dataset
construction.

## H-015 - Decision hashes are not verified against decision files

The authorization JSON contains `phase5_completion_decision_sha256` and
`phase6_entry_decision_sha256`, but the frozen CLI checks only the freeze
manifest hash. The two decision hashes are validated as uppercase SHA256-shaped
strings; arbitrary 64-character values are otherwise accepted. Thus the runner
does not substantiate its claim that the two approved decision artifacts are
actually present and hash-matched at launch.

Required correction: accept both immutable decision artifact paths, require
canonical closed schemas, hash their exact bytes, compare those hashes with the
authorization JSON, and verify that each decision binds the same freeze
manifest and the expected approval state. All checks must precede model/dataset
construction and run-root mutation.

## Static diagnostic record

The generated temporary-directory diagnostic reported:

```json
{"arbitrary_decision_hashes_accepted":true,"classification":"PHASE6-READINESS-STATIC-NO-MODEL-NO-DATA-NO-OPTIMIZER","epoch1_no_checkpoint_retry_create_new":{"type":"FileExistsError"},"formal_optimizer_steps":0,"second_seed_can_be_created_first":"seed-1747066946"}
```

The temporary directory was automatically removed. This diagnostic used no
project data and no model or optimizer.

## Governance disposition

- Preserve the existing formal-freeze tag and approval commit unchanged as the
  historical first freeze.
- Do not treat that tag as Phase 6 runnable after these findings.
- Make no runtime-source change without explicit human approval of the narrow
  corrective assembly package.
- After correction, rebuild and hash the project wheel/runtime-bound evidence,
  repeat offline reconstruction and the complete regression suite, and request
  a separate corrective-freeze completion approval and superseding annotated
  tag.
- A separate Phase 6 entry approval remains mandatory even after the corrected
  freeze is accepted.
