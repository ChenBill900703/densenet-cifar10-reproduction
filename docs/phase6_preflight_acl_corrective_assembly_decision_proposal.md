# Phase 6 Preflight/ACL Corrective Assembly Decision Package v1

Status: **APPROVED AS D-030 / CORRECTIVE ASSEMBLY AUTHORIZED / PHASE 6 EXECUTION FORBIDDEN / FORMAL OPTIMIZER CALLS 0**

Date prepared: **2026-08-24**

Evidence class: `DERIVED` for the observed control flow, ACL, and D-028 state;
`IMPLEMENTATION-ASSUMPTION` for the requested corrective policies. Nothing in
this package is a `FORMAL-REPRODUCTION-RESULT`.

## Decision context

The human selected the complete-repair direction after D-028:

- validate prepared training access and integrity before run/model mutation;
- explicitly check the execution account and effective access;
- apply a minimal read/traverse ACL grant without changing data bytes;
- add fail-before-mutation negative tests;
- rebuild the affected frozen artifacts and create a later superseding freeze;
- preserve the failed seed directory as immutable evidence;
- require a new Phase 6 entry decision for the new freeze.

That direction identifies the desired outcome, but it did not name the exact
new blockers, target account/SID, test-split boundary, artifact lineage, stop
rules, or later gate sequence. This package makes those points explicit. No
source or ACL correction may begin until the exact authorization below is
approved verbatim.

The earlier
`phase6_seed1_access_failure_disposition_proposal.md` is superseded as a
recommended path and must not be approved or used: switching back to the
sandbox account could avoid the observed ACL failure but would leave the
preflight defect in the frozen runner.

## Accepted blockers

### H-016 — execution-account/prepared-directory ACL mismatch

The approved command ran as `<REDACTED_EXECUTION_ACCOUNT>`, SID
`<REDACTED_EXECUTION_SID>`. The existing prepared CIFAR
directory cannot be traversed by that token and returns `WinError 5`. Parent
`data/` and `data/prepared/` are owned by
`<REDACTED_SANDBOX_ACCOUNT>`; the child ACL cannot even be read by the
formal execution account.

### H-017 — prepared training access is absent from preflight

The frozen `_preflight` verifies the raw archive and live software/GPU
identity, then resolves storage. It does not receive or verify
`--prepared-directory`. The CLI subsequently creates/reopens the formal seed
directory; `run_formal_training_seed` then constructs model and optimizer
before the prepared dataset is opened. Therefore an access failure can occur
after formal-root mutation and model/optimizer construction.

### H-018 — train-split verification reads test-batch bytes

`Cifar10BinaryDataset(split="train")` selects the five training batch paths,
but then calls `_verify_prepared_directory`, which SHA256-reads all six batch
files including `test_batch.bin`. This does not decode a test record, but the
strict project policy should make the training path incapable of opening test
batch bytes before all three epoch-300 training artifacts are complete.

H-018 is an `IMPLEMENTATION-ASSUMPTION` adopting the strictest interpretation
of the already frozen final-test gate. It does not claim that a test prediction
or result occurred; D-028 decoded samples and test records remain zero.

## Preserved D-028 state

The existing path
`runs/formal/64CFB2826BFE6D77CB9EE15E0BEF544186D51947C843A96C7C9F2DD9D82CABC7/seed-1021082110`
must remain unchanged as abandoned fail-closed evidence for the old freeze:

- exactly two files;
- both zero bytes and SHA256
  `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`;
- intents/completions/unresolved/accepted steps/checkpoints all zero;
- frozen H-013 empty-initial-boundary validation passed;
- D-028 report SHA256
  `CFAF5DD51FBE39CCC2879B99FE7628A7BA5BE87CE31355957B45874E3B587586`.

It may not be deleted, truncated, modified, resumed, or migrated. Because a
corrected source necessarily produces a new manifest hash and run layout, the
future corrected freeze must start in its own new manifest directory. This is
not a rerun of an accepted trajectory: the old path has zero optimizer calls.

## Authorized source correction if approved

The corrective implementation is limited to pre-execution access and
split-scoped integrity guards:

1. Freeze the formal execution identity as account
   `<REDACTED_EXECUTION_ACCOUNT>` and SID
   `<REDACTED_EXECUTION_SID>` in the new launch evidence.
2. Add a Windows execution-identity observation that compares the live account
   and SID with the new frozen identity before any prepared path or formal-root
   mutation.
3. Add a training-prepared preflight that safely resolves the directory and
   manifest, rejects symlinks/path escapes, verifies the approved archive
   identity recorded in the manifest, and opens/hashes only
   `data_batch_1.bin` through `data_batch_5.bin` against their manifest sizes
   and SHA256 values.
4. Ensure the training preflight and train-split dataset constructor do not
   stat, open, hash, map, or decode `test_batch.bin`.
5. Preserve test-batch verification for the evaluation path, but invoke it
   only after the frozen all-three-training-complete gate has passed.
6. Reorder the CLI so execution identity, canonical decisions, frozen
   artifacts/environment, prepared training access/integrity, and storage all
   pass before creating/reopening any manifest/seed run directory and before
   model, optimizer, dataset, loader, loss, backward, or optimizer activity.
7. Keep all model mathematics, dataset/archive bytes, train records,
   augmentation, RNG domains, seeds, FP32/batch 64, loss, SGD/LR, checkpoint,
   evaluation, and aggregation policies unchanged.

The account/SID choice is host-specific `IMPLEMENTATION-ASSUMPTION`, consistent
with the already host-bound GPU UUID, driver, Windows build, and exact runtime.

## Minimal ACL correction if approved

The ACL operation must be performed by the owning workspace sandbox context
and must be recorded before and after:

1. Capture owner, inheritance/protection state, explicit/inherited access
   entries, and a stable exported security-descriptor artifact for
   `data/prepared/cifar-10-batches-bin` and every required child.
2. Recompute and record every prepared file size/SHA256 before the ACL change.
3. Grant only `ReadAndExecute`/read/traverse/synchronize rights needed by
   `<REDACTED_EXECUTION_ACCOUNT>` to the prepared directory, its five training batch
   files, `test_batch.bin`, and `prepared-manifest.json`; do not grant write,
   modify, delete, ownership, or ACL-change rights.
4. Do not take ownership, replace inheritance wholesale, remove existing
   entries, or change ACLs anywhere else.
5. Recompute all file sizes/SHA256 after the ACL change and require exact
   byte-for-byte equality. Verify that the formal account can read required
   files but cannot create, modify, rename, or delete within the prepared
   directory, using temporary negative probes outside the prepared tree where
   possible and non-mutating access checks inside it.
6. If a minimal additive grant cannot be applied by the existing owner without
   ownership takeover or broader permissions, stop and request a new human
   decision. Do not copy or re-extract the dataset as a workaround.

Reading `test_batch.bin` solely to record its pre/post ACL-change SHA256 is
authorized as infrastructure-integrity evidence, not evaluation, decoding,
prediction, or a formal result. The corrected training runtime remains unable
to touch those bytes before the final-test gate.

## Mandatory negative and regression tests

All corrective tests must be static/mock or generated-only, except byte-level
prepared-file identity/access checks. They must prove:

- wrong account or SID fails before prepared access and formal-root mutation;
- missing/inaccessible/symlinked/path-escaping prepared directory fails before
  run directory, model, optimizer, dataset, or loader construction;
- inaccessible/missing/wrong-size/wrong-hash training manifest/member fails at
  the same boundary;
- training preflight and `split="train"` construction never access
  `test_batch.bin`, demonstrated by an opener/stat/hash trap;
- evaluation cannot access test bytes before all three training completions;
- the correct account with exact five training files passes preflight without
  model/dataset construction or test-byte access;
- D-024 through D-028 historical identities and the abandoned seed directory
  remain unchanged;
- existing Phase 1–5 and corrective regression suites still pass;
- no new optimizer diagnostic is added and formal optimizer calls remain zero.

## Corrective artifact and freeze sequence

If technical validation passes:

1. create a new corrective freeze-source candidate commit containing only the
   authorized source/tests/specification correction;
2. deterministically rebuild the non-editable project wheel twice and require
   byte-identical SHA256 values;
3. rebuild the offline installed-environment manifest and exact launch
   evidence; reuse the unchanged locked runtime/wheelhouse/dataset only after
   their hashes reverify;
4. create a complete Git bundle, new freeze-manifest candidate, machine report,
   ACL before/after evidence, and later freeze-record candidate commit;
5. pass project and fresh offline formal-wheel suites, source verifier,
   wheel/runtime verifier, storage gate, H-016/H-017/H-018 mutation corpus, and
   an exact-device preflight that touches no test bytes and constructs no model
   or dataset;
6. present a separate corrective-freeze completion package with every exact
   commit and SHA256 identity;
7. only after that human approval create a new annotated superseding freeze
   tag. The current corrected tag and all older tags remain immutable history;
8. prepare and obtain a new Phase 6 entry approval and new canonical decision
   capability bound to the new manifest before any formal execution.

The proposed later tag name is
`formal-freeze-densenet-bc100-12-cifar10plus-preflight-acl-corrected-2026-08-24`.
This assembly decision does not authorize creating that tag.

## Continuing prohibitions

Until both later approvals exist, no formal execution may resume or restart.
This package authorizes no model forward, CIFAR decode, loss, backward,
optimizer call, training, checkpoint, prediction, evaluation, aggregation,
pretrained result, ACL broadening, data copy/re-extraction, old-run mutation,
formal tag, or Phase 7/8 work. Formal optimizer calls remain exactly **0**.

## Exact authorization required

**「我批准 Phase 6 preflight/ACL corrective assembly decision package v1：接受 D-028 所列 H-016 execution-account／prepared-directory ACL mismatch，並接受唯讀稽核新增的 H-017 prepared training access 未在 formal-root／model／optimizer mutation 前納入 preflight，以及 H-018 `split="train"` verifier 會在三個正式訓練完成前 SHA256 讀取 `test_batch.bin` bytes；確認 decoded test records、prediction、evaluation、optimizer intents／calls、accepted steps 與 checkpoints 仍全為 0。批准僅在 static／mock／generated-only 與 byte-level prepared integrity／ACL evidence 範圍修正 runner：將正式 execution identity 固定為 `<REDACTED_EXECUTION_ACCOUNT>`／SID `<REDACTED_EXECUTION_SID>`，在任何 prepared path 或 formal-root mutation 前驗證 account／SID；在任何 run directory、model、optimizer、dataset 或 loader 建構前，安全驗證 prepared manifest 與 `data_batch_1.bin` 至 `data_batch_5.bin` 的 path／readability／size／SHA256，training preflight 與 train dataset 禁止 stat／open／hash／map／decode `test_batch.bin`，evaluation test-byte access 仍須等待三個 epoch-300 training artifacts 全部完成並驗證。批准由既有 owner context 對 `data/prepared/cifar-10-batches-bin` 及必要 children 僅新增 `<REDACTED_EXECUTION_ACCOUNT>` 的最小 ReadAndExecute／read／traverse／synchronize 權限，必須保存 ACL before／after 與所有 file size／SHA256 before／after 證據且 bytes 完全相同；禁止 take ownership、write／modify／delete／ACL-change 權限、移除既有 ACE、整體替換 inheritance、修改其他路徑、複製或重新解壓資料，若無法以最小 additive grant 完成即 fail closed。批准新增 wrong account、inaccessible／unsafe／wrong-hash training artifact、test-byte trap 與 before-mutation 負向測試，重建 corrected source／project wheel／offline environment evidence／bundle／manifest／machine report 候選；原 D-028 失敗 seed directory 及兩個 0-byte SHA256-empty files 必須永久保留且不得 delete／truncate／modify／resume／migrate。修正不得改變任何 model／data records／augmentation／RNG／seed／FP32 batch-64／loss／SGD／LR／checkpoint／evaluation／aggregation 科學規則；technical validation 完成後仍須另行批准 corrective-freeze completion package，才可建立 proposed tag `formal-freeze-densenet-bc100-12-cifar10plus-preflight-acl-corrected-2026-08-24`，之後仍須另行批准綁定新 manifest 的 Phase 6 entry；目前禁止任何正式訓練／evaluation／aggregation／formal tag，formal optimizer calls 維持 0。」**
