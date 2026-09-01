# Phase 6 Entry Decision Package v2

Status: **APPROVED 2026-08-24 AS D-035 / CANONICAL AUTHORIZATION ASSEMBLY PENDING / LIVE EXECUTION FORBIDDEN / FORMAL OPTIMIZER CALLS 0**

Date prepared: **2026-08-24**

Evidence class: `IMPLEMENTATION-ASSUMPTION` for requested execution authority
and `DERIVED` for the reverified freeze identities. This package contains no
`FORMAL-REPRODUCTION-RESULT`.

## Decision purpose

D-034 completed the preflight/ACL corrective freeze but explicitly did not
revive D-025 or authorize execution. The human approved this new Phase 6 entry
verbatim as D-035, bound only to the D-034 tag and schema-v2 manifest. Live
execution remains forbidden until the non-circular canonical authorization
assembly and fresh exact live preflight both pass.

## Sole proposed execution baseline

| Domain | Required identity |
|---|---|
| Superseding annotated tag | `formal-freeze-densenet-bc100-12-cifar10plus-preflight-acl-corrected-2026-08-24` |
| Tag object | `5695e67b37a5d5eec3fc8bedf04af0ffabf312e8` |
| Tag target / D-034 approval commit | `86e478eb49c0d3674a3a288e19d6dfe5a95803eb` |
| Corrective freeze-source commit | `47028a6b4ab38b007e59ce763cc01d21824abad0` |
| Corrective freeze-record commit | `b3a18133743b26d5e0f0054eebccd0adafdf3dae` |
| Schema-v2 corrective freeze manifest SHA256 | `15CB6FD32E5D15D33F1EAF1F716938BC80A73C1E1466E3AA44108E5E08FFDAC1` |
| Canonical config SHA256 | `C5F1B2DA0B2E0A5476531C0460313849EEB4058400BED0E0EFC3227D82A83213` |
| Approved CIFAR archive SHA256 | `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD` |
| Corrected project wheel SHA256 | `DECE8F41A0ACDDAC6869F38A3C9FE147196C799150544870CE59FB426BB7904D` |
| Python runtime archive SHA256 | `BAC14B77461752024EBF95A820B1791F2061FD2B5B368E4D3BAD9A307460716F` |
| Installed environment manifest SHA256 | `00B4D3295826F22617FCF438F6C1E344E95686729BE7F82B6F5B0C4D440CF0B0` |
| Corrective machine report SHA256 | `96304D146FD3BC1FBD9A5B039140A9D373868367C9F55345E74D169F30E0CAE7` |
| Formal execution account | `<REDACTED_EXECUTION_ACCOUNT>` |
| Formal execution SID | `<REDACTED_EXECUTION_SID>` |

Both earlier freeze tags remain immutable historical evidence and are forbidden
for future execution. D-025/D-026/D-027 are historical capability and preflight
records for the stopped D-024 baseline and may not authorize this baseline.

## Mandatory non-circular authorization assembly after approval

If the exact authorization below is approved, only this record-only sequence
may occur before live preflight:

1. Record the verbatim approval as D-035 in a dedicated approval commit. That
   commit becomes the Phase 6 v2 approval identity and changes no frozen source,
   scientific policy, dataset, wheel, runtime, environment, or manifest.
2. Create a canonical D-034 `formal-freeze-completion` JSON bound to the D-034
   approval commit and schema-v2 manifest.
3. Create a distinct canonical D-035 `phase6-entry` JSON bound to the new D-035
   approval commit and the same schema-v2 manifest.
4. Compute both decision files' exact SHA256 values and bind them, their exact
   paths, the new tag identity, and the schema-v2 manifest in a new canonical
   authorization JSON.
5. Commit those derived governance artifacts in a later record-only commit and
   verify them through the frozen runner. Any schema, decision kind, approval
   commit, file path, SHA256, tag, or manifest mismatch keeps execution closed.

This sequence avoids a circular commit identity. It authorizes no model/data
construction or formal-root mutation while the capability is being assembled.

## Mandatory exact live preflight before mutation

After canonical authorization passes, the frozen offline runtime must run a
fresh exact preflight under the fixed account and SID. Before resolving any
prepared path and before creating a formal root, seed directory, model,
optimizer, dataset, or loader, it must verify the execution identity. It must
then safely verify the prepared manifest and only `data_batch_1.bin` through
`data_batch_5.bin` for path safety, readability, size, and SHA256.

Training preflight and the train dataset must not stat, open, hash, map, or
decode `test_batch.bin`. Test-byte access remains forbidden until all three
epoch-300 training artifacts are complete, immutable, and hash-verified. The
live preflight must also reverify every freeze/environment/GPU/runtime identity,
deterministic FP32 policy, storage gate, expected new run-root state, and the
immutable D-028 evidence. Any mismatch stops before mutation.

The D-028 directory under the old manifest remains permanently abandoned. Its
two existing zero-byte SHA256-empty files may not be deleted, truncated,
modified, replaced, resumed, or migrated. The new schema-v2 manifest uses a
distinct full-manifest-hash run namespace.

## Proposed formal workflow after all preflight gates pass

Only the frozen workflow below would be authorized:

1. Train project seed `1021082110` through epoch 300 with FP32 physical batch
   64 and workers 2, retaining all 300 checkpoints and the append-only
   optimizer intent/completion ledger.
2. Hash-verify and make immutable every required seed-1 training artifact.
3. Repeat in strict order for seed `1747066946`, then seed `869460408`; no seed
   may start before its predecessor is complete and verified.
4. Only after all three epoch-300 training artifact sets are immutable and
   hash-verified may `test_batch.bin` first be accessed. Evaluate each seed
   exactly once, in the frozen order, using only its epoch-300 checkpoint.
5. Only after all three immutable evaluation records exist may the frozen
   aggregation command report each integer incorrect count, exact arithmetic
   mean, and descriptive sample standard deviation.

Each seed has 234,600 accepted trajectory steps; all three have 703,800. The
append-only ledger remains authoritative for physical optimizer calls,
including rollback replays and honest unresolved-intent crash bounds.

## Interruption and fail-closed rules

- A normal interruption may resume only from the last hash-verified completed
  epoch, rolling back and rerunning the interrupted epoch.
- An epoch-1 interruption before a checkpoint may use only the frozen
  ledger-preserving initial-boundary recovery path.
- Account/SID, prepared access, path safety, hash, environment, GPU, storage,
  order, ledger, checkpoint, finite-value, OOM, or evaluation-interruption
  failure stops automatic progress and requires a new audited disposition.
- No OOM or operational failure authorizes a change to batch, precision, AMP,
  TF32, accumulation, recomputation, compile, workers, seed, data, model, loss,
  SGD, LR, checkpoint, evaluation, aggregation, or reporting rules.
- After the first formal optimizer call, the baseline cannot change. A genuine
  bug invalidates every affected run and requires a new freeze and full rerun.

## Authority explicitly not granted

This package does not authorize either older freeze, D-028 reuse, pretrained
weights/results, post-hoc tuning, best-seed/best-epoch selection, repeated test
attempts, test-guided changes, protocol workarounds, Phase 7 conclusions, Phase
8 defense artifacts, or any claim that the paper result has been reproduced
before the complete frozen workflow and audit are finished.

## Exact human authorization

**「我批准 Phase 6 entry decision package v2：確認 annotated tag `formal-freeze-densenet-bc100-12-cifar10plus-preflight-acl-corrected-2026-08-24`、tag object `5695e67b37a5d5eec3fc8bedf04af0ffabf312e8`、tag target／D-034 approval commit `86e478eb49c0d3674a3a288e19d6dfe5a95803eb`、corrective freeze-source commit `47028a6b4ab38b007e59ce763cc01d21824abad0`、corrective freeze-record commit `b3a18133743b26d5e0f0054eebccd0adafdf3dae`、schema-v2 corrective freeze manifest SHA256 `15CB6FD32E5D15D33F1EAF1F716938BC80A73C1E1466E3AA44108E5E08FFDAC1`、canonical config SHA256 `C5F1B2DA0B2E0A5476531C0460313849EEB4058400BED0E0EFC3227D82A83213`、dataset SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD`、corrected project wheel SHA256 `DECE8F41A0ACDDAC6869F38A3C9FE147196C799150544870CE59FB426BB7904D`、Python runtime archive SHA256 `BAC14B77461752024EBF95A820B1791F2061FD2B5B368E4D3BAD9A307460716F`、installed environment manifest SHA256 `00B4D3295826F22617FCF438F6C1E344E95686729BE7F82B6F5B0C4D440CF0B0` 與 corrective machine report SHA256 `96304D146FD3BC1FBD9A5B039140A9D373868367C9F55345E74D169F30E0CAE7` 為唯一可重新申請執行的正式基線，兩個較舊 freeze tags 與 D-025／D-026／D-027 僅保留為歷史且禁止用於新執行，D-028 失敗目錄及兩個 0-byte SHA256-empty files 必須永久保持不可變且不得 resume／migrate；批准在 formal optimizer calls=0 的狀態重新進入 Phase 6，但必須先以 D-035 approval commit 非循環建立並逐位元驗證 D-034 formal-freeze-completion、D-035 phase6-entry 兩份 canonical decision JSON 及其 SHA256-bound authorization JSON，任何 schema／decision kind／approval commit／path／hash／tag／manifest 不符均禁止執行；批准僅在正式帳戶 `<REDACTED_EXECUTION_ACCOUNT>`／SID `<REDACTED_EXECUTION_SID>` 的 exact live preflight 通過後，才可建立新的 full-manifest-hash formal run namespace，且該 preflight 必須在任何 prepared path／formal-root／seed directory／model／optimizer／dataset／loader mutation 前驗證 account／SID，之後僅安全驗證 prepared manifest 與 `data_batch_1.bin` 至 `data_batch_5.bin` 的 path／readability／size／SHA256；training preflight 與 train dataset 在三個 epoch-300 training artifacts 全部 immutable 且 hash-verified 前禁止 stat／open／hash／map／decode `test_batch.bin`；批准僅使用 frozen offline runtime、corrected project wheel、approved Toronto CIFAR-10 binary archive、FP32 physical batch 64、workers=2 與 project seeds `1021082110`、`1747066946`、`869460408` 依序各完成 300 epochs，保留每 seed 300 個 checkpoints 與 append-only optimizer intent/completion ledger；批准正常中斷僅依 frozen checkpoint／epoch-1 initial-boundary 規則回滾續跑，rollback physical calls 不截斷；僅在三個 seed 的 epoch-300 training artifacts 全部 immutable 且 hash-verified 後，才可依固定順序各執行一次 final-test evaluation，之後才可依 frozen schema aggregation。任何 account／SID／prepared access／path／artifact／environment／GPU／storage／ledger／order／finite-check 失敗、OOM、unresolved intent、interrupted evaluation 或不一致狀態皆必須 fail closed 並停止自動進度，不得改變 batch、precision、AMP、TF32、accumulation、recomputation、compile、workers、seed、資料、模型、loss、SGD、LR、checkpoint、test-access、evaluation、aggregation 或 reporting 規則，不得使用 pretrained results、post-hoc tuning、best-seed／best-epoch selection、repeated test attempts 或 test-guided change；第一個正式 optimizer call 後 baseline 不可變更，正式結果完成前不得宣稱對上論文結果，Phase 7 與 Phase 8 仍須後續治理。」**
