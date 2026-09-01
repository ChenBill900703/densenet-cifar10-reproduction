# Phase 2 Completion Decision Proposal v1

Status: **HUMAN-APPROVED 2026-08-23 / PHASE 2 COMPLETED / NO PHASE 3 OR OPTIMIZER AUTHORITY**

This package was prepared after technical Phase 2 validation and before any optimizer, training, prediction, or accuracy result. The human approved it verbatim on 2026-08-23. The approval completes Phase 2 policy selection without granting later-phase or training authority.

## Approved decisions

| Decision | Approved selection | Reason |
|---|---|---|
| A-007 / H-001 / M-001 | Adopt the Toronto CIFAR-10 binary archive, exactly 170,052,171 bytes, MD5 `C32A1D4AB5D03F1284B67883E8D87530`, SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD`, as the sole formal dataset artifact. | Dataset-author source; explicitly documented binary layout; avoids pickle execution; every label/pixel is byte-exact with the separately locked official Python format. |
| Python archive role | Retain SHA256 `6D958BE074577803D12ECDEFD02955F39262C83C16FE9348329D7FE0B5C001CE` only as independent semantic-equivalence evidence, not a second selectable formal input. | Prevents multiple equivalent inputs from becoming an untracked choice. |
| Historical Torch7 archive | Keep bytes/hash/equivalence `UNKNOWN`; do not substitute a third-party copy. Accept Toronto binary as an explicit project artifact assumption. | The official-code endpoint returned HTTP 403 and supplied no digest. |
| H-003 | Approve candidate stream domain `densenet-cifar10-loader-v1`: separate SHA256-derived permutation/augmentation streams per project master seed and epoch; draw flip/x/y in global permutation order; send explicit decisions to workers. Freeze training `num_workers=2`. | Removes historical scheduling sensitivity; full 50,000-sample outputs are bit-exact for 0 and 2 workers; two workers matches the official runner default. |
| M-002 | Freeze evaluation batch size 64 and `num_workers=0`, sequential order, normalization only. | Diagnostic covered all 10,000 examples in 157 batches; no stochastic evaluation work is needed. |
| M-003 | Preserve the official rounded raw-255 constants exactly: mean `[125.3,123.0,113.9]`, std `[63.0,62.1,66.7]`; do not recompute higher-precision statistics. | Recomputed constants would change every normalized input and training trajectory. |

Derived extracted batch files remain a reconstructable cache whose six hashes are checked against the formal archive. They are not alternate formal artifacts.

## Approved scope

Approval completes Phase 2 policy selection and allows the project to document Phase 2 as complete. It does **not** start Phase 3, authorize optimizer/scheduler construction, train a model, compute accuracy, authorize a formal optimizer step, or freeze Phase 5. A separate Phase 3 entry decision is required because this authorization explicitly retains the optimizer and Phase 3 prohibitions.

## Exact human authorization

**「我批准 Phase 2 completion decision package v1：採用 SHA256 為 C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD 的 Toronto CIFAR-10 binary archive 作為唯一正式資料工件；Python archive 僅作逐位元等價證據；批准 H-003 候選 RNG/worker mapping 並固定訓練 workers=2；固定測試 batch 64、workers=0、順序載入；保留官方一位小數 normalization constants；完成 Phase 2，但仍禁止 optimizer、Phase 3 與正式訓練。」**
