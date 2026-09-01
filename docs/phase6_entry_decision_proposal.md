# Phase 6 Entry Decision Package v1

Status: **APPROVED 2026-08-24 / PHASE 6 ENTERED / SEED 1 START FAIL-CLOSED BEFORE FIRST BATCH / H-016 DISPOSITION PENDING / FORMAL OPTIMIZER CALLS 0**

Date prepared: **2026-08-24**

Evidence class: `IMPLEMENTATION-ASSUMPTION` for the requested execution
authority and `DERIVED` for the rechecked identities/readiness facts. This
document contains no `FORMAL-REPRODUCTION-RESULT`.

## Disposition of the earlier short approval

The message **「批准 Phase 6 entry decision package」** arrived before any
Phase 6 entry package or canonical Phase 6 decision artifact existed. Treating
that short message as permission to train would leave the exact execution
scope, stop rules, freeze identity, and decision-artifact hash unspecified and
would bypass the H-015 guard that D-024 just froze. It is therefore recorded as
an instruction to prepare this package, not as D-025 or as permission for a
formal optimizer call.

The exact authorization at the end of this document was later approved
verbatim on 2026-08-24. Phase 6 is therefore entered at formal optimizer steps
**0**, subject to the non-circular canonical record assembly and exact live
preflight that must pass before any model/data/formal-root mutation.

## Entry baseline

Only the following superseding corrective freeze may ever be used:

| Domain | Required identity |
|---|---|
| Corrective annotated tag | `formal-freeze-densenet-bc100-12-cifar10plus-corrected-2026-08-24` |
| Tag target / D-024 approval commit | `74266d3904a446ac7d41ee1e4fe4f79016877026` |
| Corrective freeze-source commit | `9efdd584f664df3b9f74ac9917e3b389400d61ec` |
| Corrective freeze-record commit | `29fb928c3195bc98edd95d807c7333baecd7a84f` |
| Corrective freeze manifest SHA256 | `64CFB2826BFE6D77CB9EE15E0BEF544186D51947C843A96C7C9F2DD9D82CABC7` |
| Canonical config SHA256 | `C5F1B2DA0B2E0A5476531C0460313849EEB4058400BED0E0EFC3227D82A83213` |
| Dataset archive SHA256 | `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD` |
| Corrected project wheel SHA256 | `E740FD93A0F9356F5BFCCD4C18AE67FD0D6811DD2CDF720AD78BFBE069A84338` |
| Python runtime archive SHA256 | `BAC14B77461752024EBF95A820B1791F2061FD2B5B368E4D3BAD9A307460716F` |
| Installed environment manifest SHA256 | `3DCBA6F2883C6C7E08C1BEF7AB03B73C5D7E3A3C0FE9539F479AEE51AEC8DA72` |
| Corrective machine report SHA256 | `02A173DFBBA76470AE401438841871528C203BB76B7CC7D76DBDF853FACB8F87` |

The first tag
`formal-freeze-densenet-bc100-12-cifar10plus-2026-08-23` remains immutable at
`4e69d397f7935ea2f4f9eedc83ecf43547946626` as historical evidence and is not
eligible for execution.

## Readiness facts rechecked before this proposal

- D-024 and the superseding annotated tag both resolve to
  `74266d3904a446ac7d41ee1e4fe4f79016877026`.
- The accepted project and fresh offline formal-wheel suites remain 166/166;
  the freeze verifier most recently returned `ok=true`, 20/20 wheels,
  8,264/8,264 runtime files, and formal optimizer steps 0.
- The exact approved archive/config/wheel/runtime/environment/report hashes
  were rechecked before D-024 and remained unchanged after its record commit.
- `runs/` and `runs/formal/` do not exist; no formal run artifact exists.
- The current D: free-space observation is 47,744,196,608 bytes. The frozen
  minimum is 7,164,705,960 bytes. This is a current-host observation only; the
  frozen runner must recheck storage at every mutating/result invocation.
- H-013 through H-015 are corrected and frozen by D-024. No model, CIFAR loss,
  backward, optimizer, prediction, test evaluation, or aggregation was used to
  prepare this proposal.

These facts establish decision readiness, not a guarantee that the later live
launch will pass. The exact runtime preflight must still fail closed before
model/data construction on any environmental or artifact difference.

## Non-circular canonical decision assembly after approval

If the exact authorization below is approved, the following deterministic
record-only sequence is authorized before any formal execution:

1. Commit the verbatim human authorization as D-025. That commit is the Phase 6
   approval identity; it changes no frozen source, config, manifest, wheel,
   runtime, dataset, or scientific policy.
2. Create a canonical JSON D-024 formal-freeze-completion record with
   `decision_kind="formal-freeze-completion"`, `approved=true`,
   `formal_optimizer_steps_at_approval=0`, approval commit
   `74266d3904a446ac7d41ee1e4fe4f79016877026`, and the corrective manifest hash.
3. Create a distinct canonical JSON D-025 Phase 6-entry record with
   `decision_kind="phase6-entry"`, `approved=true`,
   `formal_optimizer_steps_at_approval=0`, the new D-025 approval commit, and
   the same corrective manifest hash.
4. Compute both files' exact SHA256 values and place them, together with the
   corrective manifest SHA256, in the canonical Phase 6 authorization JSON.
5. Commit these derived governance artifacts in a later record-only commit and
   verify them with the frozen H-015 implementation. Any schema, commit, hash,
   manifest, or path mismatch leaves Phase 6 fail-closed.

This two-commit construction avoids asking a decision file to contain the hash
of the same commit that contains it. The later record commit may not modify the
frozen implementation or any scientific setting.

## Exact Phase 6 authority if approved

After the canonical decision artifacts pass H-015 and the exact live launch
preflight passes, Phase 6 authorizes only the frozen formal workflow below:

1. Create the empty base `runs/formal/`; all manifest/seed subdirectories must
   be created only by the frozen runner after preflight.
2. Train project seed `1021082110` through all 300 epochs.
3. Hash-verify its 300 checkpoints, manifests, progress, RNG state, optimizer
   state, and append-only intent/completion ledger.
4. Only then train seed `1747066946` through all 300 epochs and verify the same
   evidence.
5. Only then train seed `869460408` through all 300 epochs and verify the same
   evidence.
6. Only after all three epoch-300 training artifacts are immutable and
   hash-verified may the test split first be decoded. Evaluate each fixed seed
   exactly once, in the frozen order, using only its epoch-300 checkpoint.
7. Only after all three immutable evaluation records exist may the frozen
   aggregation command report individual integer incorrect counts, the exact
   arithmetic mean, and descriptive sample standard deviation.

Each seed has 234,600 accepted trajectory steps; all three have 703,800. The
append-only ledger, not that planned total, is the authority for reporting
physical optimizer calls. Rollback calls remain counted, and a crash window is
reported by its honest lower/upper bound.

Phase 6 entry is authorization to execute this workflow; it is not a claim that
the workflow has started, completed, matched the paper, or produced a formal
reproduction result.

## Interruption and fail-closed rules

- A normal interruption may resume only from the last hash-verified completed
  epoch, rolling back and rerunning the interrupted epoch under the frozen
  checkpoint rule.
- An epoch-1 interruption before a checkpoint may use only the frozen
  ledger-preserving `--resume-initial-boundary` path.
- An unresolved optimizer intent, inconsistent progress/ledger, malformed or
  missing checkpoint, unexpected seed directory, interrupted evaluation,
  artifact/hash mismatch, environment mismatch, storage failure, non-finite
  value, or any other validation failure stops automatic progress and requires
  a separately audited human disposition.
- OOM does not authorize a smaller batch, AMP, gradient accumulation,
  recomputation, compile, TF32, another precision, or any workaround.
- No source, config, dataset, augmentation, seed, initialization, loss,
  optimizer, LR, checkpoint, test-access, aggregation, or reporting rule may
  change after the first formal optimizer call. A genuine bug invalidates all
  affected formal runs and requires a new freeze and complete rerun.

## Authority explicitly not granted

This package does not authorize pretrained weights/results, post-hoc tuning,
best-seed/best-epoch selection, repeated test attempts, test-guided changes,
unfrozen commands, the historical first freeze, protocol workarounds, Phase 7
analysis claims, Phase 8 defense artifacts, or describing any outcome as a
paper result before the frozen workflow and audit are complete.

## Exact human authorization

**「我批准 Phase 6 entry decision package v1：確認 annotated tag `formal-freeze-densenet-bc100-12-cifar10plus-corrected-2026-08-24`、tag target／D-024 approval commit `74266d3904a446ac7d41ee1e4fe4f79016877026`、corrective freeze-source commit `9efdd584f664df3b9f74ac9917e3b389400d61ec`、corrective freeze-record commit `29fb928c3195bc98edd95d807c7333baecd7a84f`、corrective freeze manifest SHA256 `64CFB2826BFE6D77CB9EE15E0BEF544186D51947C843A96C7C9F2DD9D82CABC7`、canonical config SHA256 `C5F1B2DA0B2E0A5476531C0460313849EEB4058400BED0E0EFC3227D82A83213`、dataset SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD`、corrected project wheel SHA256 `E740FD93A0F9356F5BFCCD4C18AE67FD0D6811DD2CDF720AD78BFBE069A84338`、Python runtime archive SHA256 `BAC14B77461752024EBF95A820B1791F2061FD2B5B368E4D3BAD9A307460716F`、installed environment manifest SHA256 `3DCBA6F2883C6C7E08C1BEF7AB03B73C5D7E3A3C0FE9539F479AEE51AEC8DA72` 與 corrective machine report SHA256 `02A173DFBBA76470AE401438841871528C203BB76B7CC7D76DBDF853FACB8F87` 為唯一正式執行基線，原 2026-08-23 tag 僅保留為歷史且禁止執行；批准在 formal optimizer steps=0 的狀態進入 Phase 6，先以 D-025 approval commit 非循環建立並逐位元驗證 D-024 formal-freeze-completion、D-025 phase6-entry 兩份 canonical decision JSON 及其 SHA256-bound authorization JSON，任何 schema／commit／hash／manifest／path 不符均禁止執行；批准 exact live launch preflight 通過後，僅以 frozen offline runtime、corrected project wheel、approved Toronto CIFAR-10 binary archive、FP32 physical batch 64 與既定三個 project seeds `1021082110`、`1747066946`、`869460408` 依序各完成 300 epochs，保留每 seed 300 個 checkpoints 及 append-only optimizer intent/completion ledger；批准正常中斷僅依 frozen checkpoint／epoch-1 initial-boundary 規則回滾續跑，rollback physical calls 不截斷；僅在三個 seed 的 epoch-300 訓練工件全部 immutable 且 hash-verified 後，才可依固定順序各執行一次 final-test evaluation，之後才可依 frozen schema aggregation。任何 artifact／environment／storage／ledger／order／finite-check 失敗、OOM、unresolved intent、interrupted evaluation 或不一致狀態皆必須 fail closed 並停止自動進度，不得變更 batch、precision、AMP、TF32、accumulation、recomputation、compile、seed、資料、模型、optimizer、LR、checkpoint、test-access、aggregation 或 reporting 規則，不得使用 pretrained results、post-hoc tuning、best-seed／best-epoch selection 或 test-guided change；第一個正式 optimizer call 後 baseline 不可變更，正式結果完成前不得宣稱對上論文結果，Phase 7 與 Phase 8 仍須後續治理。」**
