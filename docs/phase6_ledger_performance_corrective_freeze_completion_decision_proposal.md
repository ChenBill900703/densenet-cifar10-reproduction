# Phase 6 Ledger-Performance Corrective Freeze Completion Decision Package v1

Status: **APPROVED AS D-045 / ANNOTATED TAG AUTHORIZED / NEW PHASE 6 EXECUTION FORBIDDEN**

Date prepared: **2026-08-24**

Approved verbatim by the human on **2026-08-25**. The approval completes the
corrective freeze and authorizes only the named annotated tag. A separate
Phase 6 entry approval remains mandatory.

Evidence class: `DERIVED`. This package accepts a technical corrective
candidate; it contains no prediction, accuracy, evaluation, aggregation, or
paper-match result.

## Candidate accepted by this decision if approved

| Item | Identity |
|---|---|
| Corrective freeze-source commit | `863375d4082abaa2a7f6580e4f90c3ec114cbce3` |
| Corrective freeze-record commit | `0ac24e07f54342428b698297db689f1408ea0f43` |
| Schema-v2 manifest | SHA256 `6CC22F7D918DF1689C4E14A33E8BB4FDAF502EF51149AF1E6537D2618547EC26` |
| Canonical config | SHA256 `C5F1B2DA0B2E0A5476531C0460313849EEB4058400BED0E0EFC3227D82A83213` |
| Dataset archive | SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD` |
| Corrected project wheel | SHA256 `D31FE8A0DFBDBF4B4100C28E587DDDA98A13EE63219B373143DF41C01F8CE859` |
| Python runtime archive | SHA256 `BAC14B77461752024EBF95A820B1791F2061FD2B5B368E4D3BAD9A307460716F` |
| Installed environment manifest | SHA256 `1E0D0EA18AE43BCBEDA2962EB363C7D8CE7FBB8B2B03000D33A8BEA130A7C953` |
| Generated scaling report | SHA256 `1A34BDD6677043DD68F8E4A49A42DC8EA554D1E06DC65015651DAF8EF4CA5878` |
| Corrective machine report | SHA256 `5BA5972212E1A55BC1BEBC28CB9AEAA69CC7235F46ECB9B1D9F51B717C137286` |
| D-043 stop report | SHA256 `8D3E7E83D654AF42CFB8DEE673BD8E0232DE48063CE586B74F13C31E2BF98F23` |

## Technical disposition

H-020 is technically corrected within the approved performance-only scope.
Incremental validation preserves the exact ledger record bytes, domains,
hashes, sequence, intent/completion ordering, append/fsync durability, full
open/recovery audit, physical bounds, and fail-closed rules. No scientific
trajectory rule changed.

Project and fresh offline formal-wheel strict suites each passed 191/191.
Two project-wheel builds were bit-identical. The fresh environment was
reconstructed offline with hashes enforced, contains 21 distributions and
23,822 RECORD files, and is bit-identical before/after testing. Both
environments verified 20/20 wheels and 8,264/8,264 runtime files. Source
verification passed 19/19 files and 5/5 repositories. Exact-account launch,
training-only prepared data, deterministic FP32, GPU identity, storage, D-028,
all prior tags, and all 62 old-run artifacts passed. `test_batch.bin` was not
accessed.

Generated corrected-ledger measurements and the accepted old-run epoch slopes
give a derived three-seed projection of 91.0979797-94.35848545 hours
(approximately 3.80-3.93 days). The disposition is
`OBSERVED-WEEK-FEASIBLE`, not a seven-day guarantee; approval/relaunch,
evaluation, contention, interruption, and recovery are not guaranteed or
fully modeled.

## Effect of approval

Approval completes this corrective freeze and authorizes creation of one
annotated tag:

`formal-freeze-densenet-bc100-12-cifar10plus-ledger-performance-corrected-2026-08-24`

It does not authorize a new Phase 6 run. All existing tags and D-028 remain
immutable. The old manifest namespace remains permanently incomplete,
abandoned, and non-resumable at exact physical interval `[24421,24421]` and
may not be combined with the new run.

After the tag is created, a separately prepared and human-approved Phase 6
entry package must bind the new tag, manifest, source/record commits, wheel,
runtime, environment, dataset, D-043 stop report, and new canonical decisions.
Only after another fresh exact-account preflight may a new manifest-hash
namespace be created and all three project seeds rerun from epoch 1 in the
unchanged order.

## Exact human authorization required

**「我批准 Phase 6 ledger-performance corrective freeze completion decision package v1：接受 corrective freeze-source commit `863375d4082abaa2a7f6580e4f90c3ec114cbce3`、corrective freeze-record commit `0ac24e07f54342428b698297db689f1408ea0f43`、schema-v2 corrective freeze manifest SHA256 `6CC22F7D918DF1689C4E14A33E8BB4FDAF502EF51149AF1E6537D2618547EC26`、canonical config SHA256 `C5F1B2DA0B2E0A5476531C0460313849EEB4058400BED0E0EFC3227D82A83213`、dataset SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD`、corrected project wheel SHA256 `D31FE8A0DFBDBF4B4100C28E587DDDA98A13EE63219B373143DF41C01F8CE859`、Python runtime archive SHA256 `BAC14B77461752024EBF95A820B1791F2061FD2B5B368E4D3BAD9A307460716F`、installed environment manifest SHA256 `1E0D0EA18AE43BCBEDA2962EB363C7D8CE7FBB8B2B03000D33A8BEA130A7C953`、generated scaling report SHA256 `1A34BDD6677043DD68F8E4A49A42DC8EA554D1E06DC65015651DAF8EF4CA5878`、corrective machine report SHA256 `5BA5972212E1A55BC1BEBC28CB9AEAA69CC7235F46ECB9B1D9F51B717C137286` 與 D-043 controlled-stop report SHA256 `8D3E7E83D654AF42CFB8DEE673BD8E0232DE48063CE586B74F13C31E2BF98F23`；接受 H-020 的 incremental-versus-full differential/property/mutation/crash/reopen 與 durability 修正證據、project/fresh offline formal-wheel 各 191/191、兩次 deterministic wheel 逐位元相同、20/20 wheels、8,264/8,264 runtime files、21 distributions、23,822 installed RECORD files、19/19 source files、5/5 repositories、正式帳戶 exact launch 與五個 training batches preflight、storage gate、D-028、舊三個 tags 及 abandoned old-run 62 個 artifacts 全部不變，並確認 training preflight 未存取 `test_batch.bin`；接受 generated-only raw timings 與舊 run epoch slopes 所得三個 seeds 約 91.0979797 至 94.35848545 小時（約 3.80 至 3.93 天）的 `OBSERVED-WEEK-FEASIBLE` DERIVED disposition，但不視為七日完成保證；完成 ledger-performance corrective freeze，並批准建立 annotated tag `formal-freeze-densenet-bc100-12-cifar10plus-ledger-performance-corrected-2026-08-24`。既有 tags 必須保留且不得移動或刪除；D-028 及舊 manifest namespace 必須永久保持 immutable／incomplete／abandoned／non-resumable，舊 run 的 24,421 次 physical calls 不得與新 run 合併或作為 seed／epoch／結果選擇依據。目前仍禁止新的 Phase 6 execution、任何新 CIFAR model forward/loss/backward/optimizer call、training、test-byte access、prediction、accuracy、evaluation、aggregation、pretrained results、post-hoc tuning 與 paper-match claim；new candidate formal optimizer calls 維持 0。正式執行必須另行建立並批准綁定新 tag／manifest／source／record／wheel／runtime／environment／dataset／D-043 stop report／canonical decisions 的 Phase 6 entry package，並在 fresh exact-account preflight 通過後，於新的 full-manifest-hash namespace 依原順序從 epoch 1 完整重跑三個 project seeds。」**
