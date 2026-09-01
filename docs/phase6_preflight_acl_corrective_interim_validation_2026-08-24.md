# Phase 6 Preflight/ACL Corrective Interim Validation

Status: **SOURCE CANDIDATE VALIDATED / ACL OWNER CONTEXT UNAVAILABLE / FAIL-CLOSED / FORMAL OPTIMIZER CALLS 0**

Date: **2026-08-24**

This is an interim technical record, not a corrective-freeze completion report
and not a `FORMAL-REPRODUCTION-RESULT`.

## Identity

| Item | Identity |
|---|---|
| D-030 approval commit | `241324bcfe68120ddbcb891247740fbcbedb6113` |
| Corrective freeze-source candidate | `d36d1db36b05405a882dcd6ea4b4205d8ed3d364` |
| Interim machine report | SHA256 `A3E69775CC16A7E8FFC759F60567C08851667D3BE59737CD8B3FCB6F38842989` |
| Deterministic project wheel | 57,916 bytes; SHA256 `EA442A88E04665096FA1BA872516DA5604203183B0B6BE5E2A2D3587C9876E19` |

## Completed technical work

- The runner now freezes and observes account
  `<REDACTED_EXECUTION_ACCOUNT>` and SID
  `<REDACTED_EXECUTION_SID>` through
  freeze-manifest schema v2 and exact launch identity.
- Historical schema-v1 freeze manifests remain verifiable as evidence but are
  explicitly ineligible for execution by the new runner.
- CLI training verifies the prepared manifest and five training batches before
  formal-root resolution/storage and before seed-directory creation.
- The direct training adapter independently verifies the same boundary before
  run-state access/mutation, device, model, optimizer, dataset, or loader.
- Train verification and `split="train"` dataset construction pass with no
  physical `test_batch.bin`; this is the H-018 no-touch oracle.
- Test-byte verification occurs only after all three immutable training
  artifacts and evaluation order pass, and before attempt files or model
  construction.
- The ACL corrective script parsed successfully and its static mutation corpus
  confirms the fixed SID/RX grant, before/after file hashes, owner/inheritance
  preservation, and absence of takeover/reset/modify/full-control commands.
- Two independent source-date-epoch project-wheel builds were byte-identical.
- The source verifier passed 19/19 files and 5/5 repositories.

## Tests

The ACL-independent project suite passed **173/173**. The complete current
suite passed **174/175**. The only failure was
`test_complete_candidate_epoch_replays_exactly_across_worker_counts`, whose
child process stopped at:

`PermissionError: [WinError 5] ... data/prepared/cifar-10-batches-bin`

The raw Toronto artifact replay passed. GPU synthetic checkpoint replay passed
bit-exact and remained generated-only. No model-math, optimizer-mechanics,
preflight-ordering, or test-byte-trap test failed.

## ACL blocker

The prepared directory owner remains
`<REDACTED_SANDBOX_ACCOUNT>`. The formal account cannot read the child
security descriptor. The sandbox owner-context process launcher repeatedly
fails before command start with
`helper_unknown_error: setup refresh had errors`.

The formal account token has Administrators only as deny-only and has no usable
backup, restore, or take-ownership privilege. Therefore no minimal grant was
attempted from that account. No ownership takeover, inheritance replacement,
ACL reset, copy, or data re-extraction was attempted.

This satisfies D-030 fail-closed behavior: the owner-context ACL before
evidence, additive RX grant, ACL after evidence, real-data replay, fresh
offline reconstruction, schema-v2 manifest, final machine report, and
corrective freeze-record candidate remain incomplete.

## Preserved D-028 evidence

The abandoned old-manifest seed directory still contains exactly:

- `optimizer-attempts.jsonl`: 0 bytes, SHA256
  `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`;
- `training-progress.jsonl`: 0 bytes, same SHA256.

No formal optimizer call, accepted step, checkpoint, test record, prediction,
evaluation, or aggregation exists.

## Legal next action

Restore the existing `<REDACTED_SANDBOX_ACCOUNT>` owner-context helper,
then run only `scripts/phase6_acl_corrective.ps1` against the approved prepared
directory. If before capture or the minimal additive grant cannot complete
without takeover/broader rights, remain fail-closed. Only after ACL and full
175/175 validation pass may offline/freeze artifact assembly continue.
