# Phase 6 Seed-1 Access-Failure Disposition Package v1

Status: **SUPERSEDED / DO NOT APPROVE OR USE / FORMAL OPTIMIZER CALLS 0**

Date prepared: **2026-08-24**

Supersession notice: the human selected a complete corrective-freeze response.
The active proposal is
`phase6_preflight_acl_corrective_assembly_decision_proposal.md`. The exact
authorization below is retained only as historical evidence and must not be
approved or executed.

Evidence class: `DERIVED` for the observed failure and `IMPLEMENTATION-ASSUMPTION`
for the requested operational recovery authority. This is not a formal result.

## Observed state

- D-025 Phase 6 entry, D-026 canonical authorization, and D-027 exact live
  preflight all passed before the command was launched.
- The only permitted seed, `1021082110`, was started through the corrected
  offline formal wheel.
- The frozen runner created the fixed seed directory and its two create-new
  files, then Windows returned `WinError 5` while resolving
  `data/prepared/cifar-10-batches-bin` under execution account
  `<REDACTED_EXECUTION_ACCOUNT>`.
- The frozen control flow constructs the model and optimizer before it opens
  the prepared dataset, so those two constructions occurred; dataset
  construction did not complete and zero samples were decoded.
- `optimizer-attempts.jsonl` and `training-progress.jsonl` are both exactly
  zero bytes, zero lines, SHA256
  `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.
- There are zero optimizer intents, zero completions, zero unresolved intents,
  zero accepted steps, zero checkpoints, and zero checkpoint manifests. The
  honest physical optimizer-call interval is `[0,0]`.
- Machine report:
  `evidence/phase6_seed1_start_failure_2026-08-24.json`, SHA256
  `CFAF5DD51FBE39CCC2879B99FE7628A7BA5BE87CE31355957B45874E3B587586`.

The failure is operational access control, not evidence of a model, dataset,
optimizer, memory, or numerical defect. It nevertheless triggers the D-025
fail-closed rule and stops automatic progress.

## Recommended disposition

Use the frozen H-013 initial-boundary recovery without changing any bytes or
ACLs:

1. Preserve the existing seed directory and both empty append-only files. Do
   not delete, truncate, replace, or recreate them.
2. Restore command execution under `<REDACTED_SANDBOX_ACCOUNT>`, the
   workspace sandbox account under which the prepared evidence was created and
   previously validated. This requires recovery of the Codex Windows sandbox
   helper; it is not a repository or scientific change.
3. Under that account, first reverify the corrective tuple, D-024/D-025
   canonical capability, prepared-directory manifest, storage, GPU/runtime
   identities, and the exact empty initial-boundary state.
4. Resume only seed `1021082110` with the frozen
   `--resume-initial-boundary` option. This reconstructs initialization from the
   project seed and preserves the existing ledger/progress history.
5. If the sandbox account cannot read the prepared evidence, cannot write the
   existing seed directory, or any identity/state differs, fail closed again
   and request a new disposition.

Changing ACLs, copying/re-extracting CIFAR to another path, deleting the seed
directory, starting a new run root, switching accounts other than the original
sandbox account, or changing any scientific/runtime rule is explicitly not
authorized by this package.

## Exact authorization required

**「我批准 Phase 6 seed-1 access-failure disposition package v1：接受 SHA256 為 `CFAF5DD51FBE39CCC2879B99FE7628A7BA5BE87CE31355957B45874E3B587586` 的 fail-closed machine report，確認 seed `1021082110` 在 `<REDACTED_EXECUTION_ACCOUNT>` 帳戶存取既有 `data/prepared/cifar-10-batches-bin` 時因 `WinError 5` 停止；確認 model／optimizer 已依 frozen control flow 建構但 dataset 未完成建構、decoded samples=0、optimizer intents=0、completed calls=0、unresolved intents=0、accepted steps=0、checkpoints=0、formal optimizer-call interval=`[0,0]`。批准保留既有 seed directory 與兩個 SHA256 均為 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` 的 0-byte ledger／progress files，不得刪除、截斷、替換或重建；僅批准在 Codex Windows sandbox helper 恢復後，改由原 `<REDACTED_SANDBOX_ACCOUNT>` workspace sandbox 帳戶重新驗證 corrective tuple、D-024／D-025 canonical authorization、prepared manifest、GPU/runtime/storage 與 H-013 empty initial-boundary state，全部通過後以 frozen `--resume-initial-boundary` 繼續同一 seed。不得修改 ACL、複製或重新解壓 CIFAR 至其他路徑、建立另一 run root、改用其他 execution account，亦不得變更任何 frozen scientific／runtime rule；若 sandbox 帳戶仍無法讀取 prepared evidence、無法寫入既有 seed directory 或任何 identity／state 不符，必須再次 fail closed 並另行請示；formal optimizer calls 在第一個 ledgered call 前維持 0。」**
