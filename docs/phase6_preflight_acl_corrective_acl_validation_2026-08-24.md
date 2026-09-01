# Phase 6 Preflight/ACL Corrective Access Validation

Status: **ACL TECHNICALLY CORRECTED / ARTIFACT REBUILD IN PROGRESS / FORMAL EXECUTION FORBIDDEN**

Date: **2026-08-24**

This is `DERIVED` technical evidence under D-030 and D-032. It is not a
formal freeze, Phase 6 re-entry, training result, or
`FORMAL-REPRODUCTION-RESULT`.

## Sandbox helper recovery

Codex sandbox setup failed before command creation because Windows denied its
managed `.git` ACE update. D-032 authorized one explicit, non-inheriting
`WRITE_DAC/ChangePermissions` ACE for `<REDACTED_EXECUTION_ACCOUNT>` on `.git`.
The evidence proves that `.git` owner, inheritance protection, non-target ACEs,
Git objects, index, tracked working-tree bytes, HEAD, and clean state were
unchanged. The owner-context helper then executed successfully as
`<REDACTED_SANDBOX_ACCOUNT>`.

| Evidence | SHA256 |
|---|---|
| Helper before | `78FEE8CC78B400B700F8864868CE1AB1B51A4BEBBADE9FAED0482B5C008951DA` |
| Helper after | `02A558E998F721F901C08ED6EE03D4C5885DE3102D644B067B286C43A0F943C9` |
| Helper report | `FAC9550C9BB5019BAFEB9C24B962E207BFFD89D020DEBAA2FA680C35B2E88B41` |

## Prepared-directory correction

The first owner-context grant attempt stopped during post-validation because
Windows `icacls /T` unexpectedly changed the protected root's inheritance
control state and introduced parent inherited ACEs. The failure snapshot was
preserved. No data byte changed.

The root protection Boolean was restored to its before state; the inherited
parent ACEs introduced by that drift were removed; the approved RX/synchronize
ACE was retained. Final semantic comparison confirms identical path, owner,
protection, and every non-target ACE on the root and seven approved files. The
only access-rule delta is the approved account's root RX/synchronize ACE,
inherited by the files.

| Evidence | SHA256 |
|---|---|
| ACL before | `63E2E95FD419DCD961C4DB516ACBD6B1A5F3EDE1FB8002DE0190BACC5B822C60` |
| Drift/failure snapshot | `F03F9305CB9465878CE4DBF18ED94725BF75761986149A4D95D2243091192992` |
| ACL after | `044404FB28A52585240E705087E1C74C0B84A0D60E9A0AD92E26A9D0BA2146F3` |
| ACL report | `8BEB9FD5506D74410EA064B113C1A43DB6C0589F1784EF9E11BC0346F46E4BD1` |

The repository mutation script now adds one inheritable rule to only the
protected root through `Set-Acl`; it no longer invokes `icacls.exe /T`.
Validation treats ACE order as non-semantic while still requiring exact SID,
Allow/Deny type, rights mask, inheritance flags, propagation flags, and
inherited/explicit state.

## Validation result

- Project strict suite: **175/175 passed**.
- ACL guard subset: **9/9 passed**.
- Source verification: **19/19 files and 5/5 repositories passed**.
- Exact `<REDACTED_EXECUTION_ACCOUNT>` data-pipeline replay passed for 50,000
  training records with workers 0/2 bit-exact and the existing 10,000-record
  diagnostic.
- That replay constructed no model or optimizer, executed zero optimizer
  steps, and computed no accuracy.
- D-028 still contains only the two zero-byte SHA256-empty ledger/progress
  files.

Formal optimizer calls remain exactly **0**. Corrective wheel, offline
environment, bundle, schema-v2 manifest, machine report, completion approval,
superseding tag, and a new Phase 6 entry remain required.
