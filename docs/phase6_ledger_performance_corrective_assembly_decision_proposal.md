# Phase 6 Ledger-Performance Corrective Assembly Decision Package v1

Status: **APPROVED AS D-042 / CONTROLLED STOP AND CORRECTIVE ASSEMBLY AUTHORIZED / NEW FORMAL EXECUTION FORBIDDEN**

Date prepared: **2026-08-24**

Evidence class: `DERIVED` for the observed runtime growth, frozen-source control
flow, current formal state, and projections; `IMPLEMENTATION-ASSUMPTION` for
the proposed administrative-stop and incremental-verification design. This
package contains no accuracy, prediction, evaluation, or paper-match result.

## Decision context

The professor's maximum available wall time is one week. The active corrected
freeze remains scientifically unchanged and the seed-1 process remains
healthy, but the frozen audit implementation makes that deadline infeasible.
The canonical readiness report is:

`evidence/phase6_ledger_performance_corrective_readiness_2026-08-24.json`

SHA256:

`F8B28DF76FC63A6281C243838EE28D8DC4BA3353DFBA30190480BEBC37D6CA33`

At the report snapshot, seed `1021082110` was active with 29 immutable
checkpoint/manifest pairs, no stderr, no final-test artifact, no later-seed
directory, and at least 23,887 completed physical calls. Because training
continues until this proposal is approved, those dynamic counts are not the
future stop boundary. The stop boundary must be measured after the approved
administrative stop and may never be backfilled from this snapshot.

## H-020 — full-history verification on every append

The frozen source `src/densenet_reproduction/phase5.py`, SHA256
`F9D1C7ED43A20688DEE7F5EC51BBC51A17A5BE2B5B70D5784D909BF6768A42F6`,
has these relevant operations:

- `formal_runtime.py:47` appends an intent before an optimizer call;
- `formal_runtime.py:54` appends its completion after the call;
- `phase5.py:410` calls `verify_attempt_records(self._records)` after every
  append.

Thus every physical optimizer call performs two growing full-history scans.
The ledger remains correct, canonical, durable, and auditable, but total
verification work grows quadratically with the number of calls.

Measured checkpoint intervals increased from 806.417 seconds at epoch 15 to
1,187.785 seconds at epoch 29. Linear fits over all 15 post-resume intervals
and the last ten intervals give slopes of 29.517 and 28.027 seconds per later
epoch. Under those observed models:

- seed 1 alone has approximately 377.57–393.17 hours remaining;
- all three sequential seeds have approximately 1,150.35–1,197.11 hours
  remaining before final evaluation.

Those are projections, not guarantees. They are sufficient to classify the
current frozen runner as incompatible with a seven-day deadline. H-020 is a
performance/governance blocker, not evidence of incorrect model mathematics
or an incorrect trajectory.

## Consequence of the immutable baseline

The first formal optimizer call already made the current baseline immutable.
The active runner may not be patched in place, monkey-patched, resumed through
new code, or given a replacement ledger implementation. Doing so would mix
two source identities in one formal run.

The only auditable correction is therefore:

1. administratively stop and permanently abandon the current incomplete run;
2. preserve every current artifact as historical formal-attempt evidence;
3. build and validate a new performance-only corrective source and freeze;
4. obtain separate corrective-freeze completion approval;
5. obtain a separate Phase 6 entry approval bound to the new tag/manifest;
6. start all three seeds again from epoch 1 in a new manifest-hash namespace.

The incomplete old run may never be reported as a completed reproduction,
combined with the new run, resumed under the new source, or used to select a
seed, epoch, hyperparameter, or result.

## Authorized administrative stop if approved

Approval authorizes one bounded, evidence-first stop of the exact active seed-1
formal process tree. It does not authorize stopping unrelated applications or
changing the computer, GPU, data, or old artifacts.

Before sending any stop signal:

1. resolve the live wrapper, frozen-runtime trainer, DataLoader workers, and
   console helper from their parent/child identities and exact command lines;
2. require every targeted Python command to name seed `1021082110`, the
   current manifest SHA256, and the approved frozen runner;
3. capture account/SID, process IDs, creation times, GPU process state,
   current stderr/stdout sizes, complete artifact listing, latest complete
   checkpoint/manifest, ledger/progress tails, and file sizes/hashes needed to
   identify the boundary;
4. confirm that no seed 2/3 or final-test/evaluation artifact exists.

After those checks, request one cooperative interrupt of only the verified
project process tree and allow up to 60 seconds for exit. If cooperative
interrupt is unavailable or the exact tree remains alive, terminate only the
verified child processes and wrapper, child-first. Do not reboot Windows,
reset the GPU, kill unrelated Python processes, or delete any file. If target
identity changes or cannot be proven, fail closed without signaling.

After exit:

- require no project trainer, worker, wrapper, or project GPU process to
  remain;
- read the complete ledger and progress exactly as left on disk;
- record intents, completions, unresolved intents, physical lower/upper bound,
  accepted coordinate, ledger head, latest complete checkpoint, log bytes,
  and any temporary/torn artifact;
- classify the stop as
  `HUMAN-DEADLINE-PERFORMANCE-CORRECTIVE-ABANDONMENT`, never `UNKNOWN`, OOM,
  normal completion, or a scientific failure;
- preserve a possible final unresolved intent honestly as a physical-call
  interval; never synthesize a completion or infer whether the GPU call
  occurred;
- mark the old namespace permanently abandoned and non-resumable.

Every old ledger, progress record, checkpoint, manifest, log, D-028 artifact,
and freeze tag must remain byte-identical after the stop. They may not be
deleted, truncated, renamed, replaced, migrated, compacted, or reused.

## Authorized source correction if approved

The new source correction is limited to ledger verification performance. It
must preserve all existing canonical record fields, hash domains, record
hashes, sequence rules, intent/completion ordering, `fsync` durability,
unresolved-intent bounds, checkpoint provenance, public full-ledger verifier,
and fail-closed recovery semantics.

The implementation may:

1. fully parse and call the unchanged public `verify_attempt_records` once
   when an existing ledger is opened;
2. derive an in-memory verified state containing the last sequence/hash,
   pending-intent map, intent/completion counts, and physical-call bounds;
3. validate each proposed intent or completion against that state without
   rescanning earlier records;
4. compute the same record SHA256, append the same canonical JSON line, and
   `fsync` it before treating the record as durable;
5. update in-memory state only after the durable append succeeds;
6. reconstruct state by a complete unchanged verification after every process
   restart, interruption, or resume;
7. retain an explicit full-ledger audit path for readiness, finalization, and
   offline evidence generation.

A crash after durable write but before in-memory state update is handled by
the next process's complete read/verification. A partial/torn write continues
to fail closed. No automatic repair, truncation, completion synthesis, or
ledger rewriting may be added.

The correction may not change:

- model code, parameter order, initialization, BatchNorm, logits, loss,
  backward, optimizer, momentum, Nesterov, weight decay, LR, or update order;
- dataset archive/prepared bytes, decoded records, augmentation, samplers,
  workers, RNG mappings, seeds, batch size, precision, deterministic policy,
  AMP, TF32, compile, accumulation, or recomputation;
- accepted-step coordinates, checkpoint contents/rules, storage rule, seed
  order, test-access gate, evaluation, aggregation, or reporting schema.

No old checkpoint may be loaded by the new source. The corrected execution
must begin seed `1021082110` at epoch 1 in a new full-manifest-hash namespace.

## Mandatory validation

Validation before a corrective completion request is limited to static/mock,
generated-only, and existing byte-level artifact verification. It must not
perform a CIFAR model forward, CIFAR loss/backward/optimizer call, test decode,
prediction, accuracy, evaluation, aggregation, or pretrained-result access.

The candidate must pass:

1. a source allowlist proving that scientific model/data/RNG/training files
   and frozen configuration values did not change;
2. differential property tests showing the incremental state produces the
   same record bytes, SHA256 heads, summaries, pending intents, and rejection
   decisions as the unchanged full verifier for generated valid and invalid
   ledgers;
3. mutation tests for wrong sequence/hash, cross-intent completion, duplicate
   completion, missing intent, torn line, partial write, write failure,
   `fsync` failure, crash before call, crash during call, crash after call,
   and crash after durable completion;
4. reopen/recovery tests proving one complete verification occurs before any
   append and that no append path invokes a growing full-history scan;
5. existing generated-only checkpoint/replay and deterministic mechanics
   regression tests, with no new CIFAR optimizer diagnostic;
6. generated-ledger scaling measurements at multiple record counts, reporting
   raw append/reopen/full-audit timings without inventing or silently applying
   an automatic universal headroom threshold;
7. complete project and fresh offline formal-wheel suites, source verification,
   wheel/runtime/environment verification, exact-account launch preflight,
   storage gate, and D-028/old-run immutability checks.

The completion package must report an `OBSERVED-WEEK-FEASIBLE` or
`OBSERVED-WEEK-NOT-FEASIBLE` disposition with the raw measurements and an
explicit projection. Only the human may accept that disposition. No seven-day
completion guarantee may be claimed.

## Corrective artifact and approval sequence

If all authorized validation passes:

1. create a corrective freeze-source candidate commit;
2. deterministically build the project wheel twice and require identical
   SHA256 values;
3. rebuild the installed-environment evidence, source bundle, schema-v2
   freeze-manifest candidate, and machine report;
4. reverify the unchanged dataset, Python runtime, wheelhouse, account/SID,
   GPU, deterministic policy, prepared five training files, storage, older
   tags, D-028, and the abandoned old run;
5. create a later freeze-record candidate commit;
6. prepare a separate corrective-freeze completion decision package;
7. only after its exact human approval, create proposed annotated tag
   `formal-freeze-densenet-bc100-12-cifar10plus-ledger-performance-corrected-2026-08-24`;
8. prepare and obtain a separate new Phase 6 entry approval bound to that tag,
   manifest, wheel, runtime, environment, dataset, stop report, and canonical
   decisions;
9. pass a fresh exact live preflight before creating the new run namespace;
10. start all three project seeds from epoch 1 in their unchanged frozen order.

The two prior corrected tags and the original tag remain immutable historical
evidence and may not be moved or deleted. The current preflight/ACL-corrected
tag becomes execution-ineligible after the administrative abandonment but
remains valid historical evidence.

## Continuing prohibitions

This assembly approval alone does not authorize the corrected formal run,
Phase 6 re-entry, a new CIFAR model forward/loss/backward/optimizer call,
test-byte access, prediction, accuracy, evaluation, aggregation, seed
selection, pretrained results, post-hoc tuning, or any claim of matching the
paper. Old formal physical calls remain permanently reported under the old
manifest and are never added to the new run's counts.

Until the later corrective completion and Phase 6 entry approvals, formal
optimizer calls under the new candidate remain zero.

## Professor-facing interpretation

The honest explanation is: the first formal attempt exposed a performance
defect in the audit mechanism, not a DenseNet mathematical error. The project
preserves that attempt, changes only the audit algorithm through a new
reviewed freeze, revalidates semantic equivalence, and reruns every seed from
the beginning. The one-week estimate is a measured projection, not a promised
paper result.

## Exact human authorization

**「我批准 Phase 6 ledger-performance corrective assembly decision package v1：接受 canonical readiness report SHA256 `F8B28DF76FC63A6281C243838EE28D8DC4BA3353DFBA30190480BEBC37D6CA33` 所記錄的 H-020：目前 frozen runner 在每個 optimizer intent 與 completion append 後重新掃描完整 ledger，造成累積二次方驗證成本；接受 epoch 15 至 epoch 29 checkpoint interval 由 806.417 秒增加至 1,187.785 秒、觀測斜率 28.027 至 29.517 秒／epoch，以及目前 frozen runner 無法在教授七日期限內完成三個 seeds 的 `DERIVED` 判定；確認此為 audit-performance/governance blocker，不是模型、資料、loss、optimizer、RNG、checkpoint trajectory 或目前已保存 bytes 的正確性失敗。批准在 source mutation 前先對 seed `1021082110` 的正式 process tree、exact command/account/SID/GPU、logs、artifact listing、latest checkpoint、ledger/progress tail、later-seed 與 test/evaluation absence 建立 before-stop 證據，之後僅對逐位元確認屬於目前 manifest／seed／frozen runner 的 wrapper、trainer、workers 與 console helper 執行一次受控停止：先嘗試 cooperative interrupt 並等待最多 60 秒，若不可用或未退出，才可 child-first 終止同一個已驗證 project process tree；禁止 reboot、GPU reset、停止不相關程序或刪除任何檔案。停止後必須確認沒有 project Python/GPU process，完整驗證停止時 ledger／progress／checkpoint／manifest／logs，誠實記錄 intents、completions、unresolved intents、physical-call interval、accepted coordinate、ledger head 與任何 temporary/torn artifact；停止原因固定為 `HUMAN-DEADLINE-PERFORMANCE-CORRECTIVE-ABANDONMENT`，不得改寫為 `UNKNOWN`、OOM、正常完成或科學失敗；即使存在最後 unresolved intent 也只能保留誠實上下界，不得補 completion、推定 GPU call、truncate 或修復。批准將目前舊 namespace 永久標記為 incomplete／abandoned／non-resumable，所有既有 ledger、progress、checkpoint、manifest、logs、D-028 與 tags 必須永久保留且不得 delete／truncate／rename／replace／migrate／compact／resume，也不得把舊 checkpoint、calls 或 trajectory 合併至新 run。批准僅在 static／mock／generated-only 與既有 byte-level artifact verification 範圍修正 ledger：existing ledger open／restart／resume 時仍以 unchanged `verify_attempt_records` 完整驗證一次並重建 last sequence/hash、pending intents、intent/completion counts 與 physical bounds；每個新 record 僅以該 verified in-memory state 做等價 incremental validation，產生完全相同 canonical JSON、hash domain、record SHA256、sequence、intent-before-call／completion-after-call、append 與 fsync durability，durable append 成功後才更新 memory；保留 public full-ledger audit path，torn／partial／write／fsync／crash 狀態一律 fail closed，禁止自動 repair、truncate、completion synthesis 或 ledger rewrite。修正不得改變任何 model／parameter／initialization／BatchNorm／data bytes／records／augmentation／sampler／workers／RNG／seed／FP32 batch-64／deterministic policy／logits／loss／backward／SGD／LR／update order／accepted-step／checkpoint／storage／seed order／test-access／evaluation／aggregation／reporting 科學規則，且新 source 禁止載入任何舊 checkpoint；必須新增 incremental-versus-full differential/property/mutation/crash/reopen 測試、source allowlist、generated-ledger scaling raw measurements，並重跑既有 generated-only checkpoint/replay regression、project/fresh offline formal-wheel、source/wheel/runtime/environment、exact-account preflight、storage、D-028 與 old-run immutability 驗證，不得新增 CIFAR optimizer diagnostic、test decode、prediction、accuracy、evaluation、aggregation 或 pretrained-result access。批准重建 corrective source、deterministic project wheel、installed-environment evidence、source bundle、schema-v2 manifest、machine report 與 freeze-record 候選；completion package 必須以 raw timings 報告 `OBSERVED-WEEK-FEASIBLE` 或 `OBSERVED-WEEK-NOT-FEASIBLE`，不得保證七日完成。技術完成後仍須另行批准 corrective-freeze completion package，才可建立 proposed annotated tag `formal-freeze-densenet-bc100-12-cifar10plus-ledger-performance-corrected-2026-08-24`；之後仍須另行批准綁定新 tag／manifest／wheel／environment／dataset／stop report／canonical decisions 的 Phase 6 entry，且三個 project seeds 必須在新 full-manifest-hash namespace 從 epoch 1 依原順序全部重跑。此 assembly approval 本身不授權新 Phase 6 execution、任何新 CIFAR model forward/loss/backward/optimizer call、test-byte access、prediction、accuracy、evaluation、aggregation、seed selection、post-hoc tuning、pretrained results 或 paper-match claim；新 candidate formal optimizer calls 維持 0。」**
