# Phase 6 Seed-1 Unknown-Interruption / Epoch-13 Rollback Resume Disposition Package

Status: **APPROVED 2026-08-24 AS D-039 / PRE-RESUME REVERIFICATION REQUIRED / TRAINING STOPPED**

Date prepared: **2026-08-24**

Evidence class: `DERIVED` for the observed stopped state and
`IMPLEMENTATION-ASSUMPTION` for the requested human disposition. This package
does not contain an accuracy, evaluation, or completed reproduction claim.

## Decision purpose

The formal seed `1021082110` process is no longer running. It stopped during
epoch 14 after batch index 761 without a terminal exit status. The artifacts
prove an internally consistent stopped state, but they do not prove why the
process stopped. The cause therefore remains `UNKNOWN`; it must not be silently
described as a normal interruption, OOM, application crash, or GPU failure.

The human requested this package after asking to restart safely and later
approved its exact authorization verbatim as D-039. The retained-call and
fail-closed consequences below are now binding.

## Locked readiness evidence

Canonical readiness report:
`evidence/phase6_seed1_unknown_interruption_epoch13_resume_readiness_2026-08-24.json`

SHA256:
`DFF3395007868C37F767097BED66D32DF8479762C8B68BD4F5E29AA91998BC7E`

Verified state:

- 10,928 intents and 10,928 completions; unresolved intents `0`; physical-call
  interval exactly `[10928,10928]`.
- All 13 checkpoint/manifest pairs and the complete progress log passed frozen
  hash-chain, canonical JSONL, finite-loss, and provenance checks.
- Latest immutable checkpoint:
  `epoch-013.pt`, 6,619,581 bytes, SHA256
  `026242A4021389B4046E6C80A9BEB0DCB0B088B9D151A52D3F5225D4CFF45260`.
- Epoch-13 manifest SHA256:
  `6A4705F0DE6C1B1E5C221EBAAC850B60B700D14CEBEB017B646CD1C41115812A`.
- Epoch-13 accepted trajectory boundary: 10,166 calls; ledger head
  `6BE31582797423EE3C4865FBF7E0FBAD28AF27F11A1C3915A16166E436008C85`.
- Interrupted epoch 14 contains 762 completed physical calls through batch
  index 761; last accepted-step coordinate 10,928; last ledger head
  `4490516B9F02F4A51C871B2BB2B18342B2D386F2FE2464D6D9DD73C058E419F7`.
- No Python/GPU training process, temporary checkpoint, partial manifest,
  later-seed directory, test/evaluation artifact, or unresolved intent exists.
- D-028 remains exactly two immutable zero-byte SHA256-empty files.
- Windows Application/System events contain no Python crash, OOM, GPU-driver,
  display-reset, sleep, or power-failure evidence in the stop interval. One
  unrelated Codex DCOM 10016 warning exists. Absence of those records does not
  determine the cause.

## Proposed human disposition

If approved, D-039 will classify this exact `UNKNOWN`-cause state as eligible
for the already frozen epoch-boundary rollback mechanism. It will not change
the cause classification and will not claim that the first epoch-14 attempt is
part of the accepted trajectory checkpoint.

The 10,928 completed physical calls remain permanently recorded. The resume
must load only `epoch-013.pt`, restore its model/optimizer/RNG state, and rerun
epoch 14 from batch index 0 under the unchanged frozen data/RNG mapping. The
runner must use `--resume-checkpoint`; `--resume-initial-boundary`, a new seed
directory, a new run namespace, or a fresh epoch-1 run is forbidden.

If epoch 14 then completes without another interruption, its accepted
trajectory boundary will be 10,948, while the physical-call interval will be
exactly `[11710,11710]`: 10,928 retained calls plus 782 replay calls. This
difference is required audit evidence, not an error and not permission to
truncate the first attempt.

## Mandatory pre-resume sequence

After exact approval and before model/optimizer construction:

1. Commit the verbatim D-039 human authorization as a record-only decision.
2. Reverify the D-034/D-035 authorization, manifest/config/dataset/wheel/
   runtime/environment/GPU identities, account/SID, deterministic FP32 policy,
   prepared manifest and only the five training batch files, storage, D-028,
   later-seed absence, the complete append-only ledger/progress logs, and all
   13 checkpoints.
3. Require the latest usable checkpoint to remain exactly `epoch-013.pt` with
   the identities above and require unresolved intents to remain zero.
4. Invoke only the frozen offline runner for seed `1021082110` with
   `--resume-checkpoint <exact epoch-013.pt>`.

Any failure before the runner call leaves the run stopped and unchanged.

## Fail-closed rules after resume

- Existing ledger/progress/checkpoints and D-028 may not be deleted, truncated,
  replaced, renamed, migrated, or edited.
- Any new OOM, account/SID mismatch, artifact/hash/path/environment/GPU/storage
  mismatch, checkpoint/progress/ledger inconsistency, unresolved intent,
  non-finite value, unexpected process exit, or protocol discrepancy stops
  automatic progress. No second automatic resume is authorized by D-039.
- Batch, precision, AMP, TF32, accumulation, recomputation, compile, workers,
  seeds, data, model, loss, SGD, LR, checkpoint, evaluation, aggregation, and
  reporting rules remain unchanged.
- Test bytes, evaluation, prediction, accuracy, aggregation, seed 2, and seed 3
  remain forbidden until the frozen training-order gates are satisfied.

## Exact human authorization

**「我批准 Phase 6 seed-1 unknown-interruption／epoch-13 rollback resume disposition package v1：接受 canonical readiness report SHA256 `DFF3395007868C37F767097BED66D32DF8479762C8B68BD4F5E29AA91998BC7E` 所記錄的停止原因維持 `UNKNOWN`，並確認目前沒有正式 Python/GPU training process、OOM／GPU-driver／power-event 證據、temporary／partial checkpoint、later-seed directory、test/evaluation artifact 或 unresolved optimizer intent；接受 seed `1021082110` 的 append-only ledger 為 10,928 intents、10,928 completions、unresolved intents 0、physical optimizer-call interval `[10928,10928]`，以及 13 個 checkpoint／manifest 與完整 progress log 已通過 frozen hash-chain、canonical、finite-loss 與 provenance 驗證；接受唯一合法 rollback checkpoint `epoch-013.pt` 為 6,619,581 bytes、SHA256 `026242A4021389B4046E6C80A9BEB0DCB0B088B9D151A52D3F5225D4CFF45260`，其 manifest SHA256 `6A4705F0DE6C1B1E5C221EBAAC850B60B700D14CEBEB017B646CD1C41115812A`、accepted trajectory boundary 10,166、ledger head `6BE31582797423EE3C4865FBF7E0FBAD28AF27F11A1C3915A16166E436008C85`；批准將此 exact `UNKNOWN`-cause stopped state 人工處置為可依 frozen epoch-boundary rollback 規則恢復，但不得改寫原因為正常中斷、OOM 或其他已知原因；批准先以 record-only commit 記錄 D-039，並在任何 model／optimizer／dataset object／loader mutation 前重新驗證 D-034／D-035 authorization、manifest／config／dataset／wheel／runtime／environment／GPU、正式 account／SID、deterministic FP32 policy、prepared manifest 與僅五個 training batch files、storage、D-028、later-seed absence、完整 ledger／progress 與全部 13 checkpoints；全部通過後，僅可使用 frozen offline runner、原 seed directory 與 `--resume-checkpoint` 指向 exact `epoch-013.pt`，保留既有 10,928 completed physical calls 且不得 truncate／delete／replace／rename／migrate 任何 ledger、progress、checkpoint、manifest、D-028 或 run artifact，禁止 `--resume-initial-boundary`、新 seed directory、新 namespace 或從 epoch 1 重新開始；批准完整重跑 epoch 14 的 782 calls，若 epoch 14 成功發布 checkpoint，預期 accepted trajectory boundary 為 10,948、physical optimizer-call interval 為 `[11710,11710]`，其中既有 interrupted epoch-14 的 762 calls 必須永久保留為 rollback physical-call evidence。任何新 OOM、account／SID／artifact／hash／path／environment／GPU／storage／checkpoint／progress／ledger 不一致、unresolved intent、non-finite value、unexpected process exit 或 protocol discrepancy 均必須 fail closed 並停止自動進度，D-039 不授權第二次自動 resume 或任何 batch、precision、AMP、TF32、accumulation、recomputation、compile、workers、seed、data、model、loss、SGD、LR、checkpoint、test-access、evaluation、aggregation、reporting 變更；在 seed `1021082110` epoch 300 training artifacts 完整 immutable 且 hash-verified 前，仍禁止 seed 2、seed 3、test bytes、evaluation、prediction、accuracy 與 aggregation。」**
