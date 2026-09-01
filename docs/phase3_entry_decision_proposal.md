# Phase 3 Entry Decision Proposal v1

Status: **HUMAN-APPROVED 2026-08-23 / PHASE 3 SYNTHETIC-MECHANICS AUTHORITY / NO FORMAL TRAINING**

Date prepared: **2026-08-23**

This package was prepared after Phase 2 completion and before any optimizer was
constructed or stepped.  The human approved it verbatim on 2026-08-23.  It
grants an exact, testable boundary for training-mechanics validation without
authorizing CIFAR optimization, accuracy measurement, a formal run, Phase 4,
or the Phase 5 freeze.

## 1. Evidence-backed mechanics

| Item | Evidence | Required Phase 3 interpretation |
|---|---|---|
| Loss | Official `models/init.lua:117`; historical `CrossEntropyCriterion.lua:3-7`; `ClassNLLCriterion.lua:4-6` | Raw logits, no class weights, mean cross-entropy over the physical batch, no label smoothing |
| Optimizer | Paper p.5; official `train.lua:19-31,78` | SGD, learning rate 0.1 initially, momentum 0.9, Nesterov enabled, dampening 0, coupled weight decay `1e-4` |
| Weight-decay scope | Official `model:getParameters()` plus historical `optim/sgd.lua:46-54` | One logical set containing every trainable tensor; do not exclude BatchNorm affine parameters or classifier bias |
| First/subsequent momentum steps | Historical `optim/sgd.lua:57-67`; installed PyTorch `torch/optim/sgd.py:353-379` | Add coupled decay before momentum; initialize the buffer from that gradient; apply Nesterov as `g + momentum*buffer` |
| Learning-rate boundary | Official `train.lua:37-40,188-198` with 300 epochs | Set LR before the first update of each epoch: 0.1 for 1-149, 0.01 for 150-224, 0.001 for 225-300 |
| Public checkpoint | Official `checkpoints.lua:27-65` | Epoch model and optimizer state are evidence-backed, but the public schema lacks project RNG/data cursor/config-hash guarantees and saves a forbidden best-test model |

The optimizer translation is a semantic port, not a claim that separate PyTorch
tensor kernels are bitwise identical to the historical flattened Torch7 kernel.
Phase 3 must independently test the approved equations and current runtime.

## 2. Approved decisions

### A-009 - Exact modern SGD port

Construct exactly one `torch.optim.SGD` parameter group containing all 299
trainable tensors once, in `model.named_parameters()` order, with:

- `lr` assigned by the explicit epoch function below;
- `momentum=0.9`;
- `dampening=0.0`;
- `weight_decay=1e-4`;
- `nesterov=True`;
- `maximize=False`;
- `foreach=False`;
- `fused=False`;
- `differentiable=False`.

No decoupled weight decay, parameter exclusions, multiple parameter groups,
gradient clipping, gradient accumulation, AMP scaling, fused path, foreach path,
or optimizer closure is permitted.  Before every synthetic test backward pass,
clear gradients explicitly and then require a finite gradient for every one of
the 299 trainable tensors before calling `step()`.

### H-004 - Explicit epoch learning-rate function

Do not use a stateful PyTorch scheduler object.  Mirror the official runner by
setting the sole optimizer group's LR at epoch start from a fail-closed pure
function:

| Epoch | LR |
|---:|---:|
| 1-149 | `0.1` |
| 150-224 | `0.01` |
| 225-300 | `0.001` |

Reject epochs outside 1-300.  Checkpoint resume derives the next LR from the
next epoch number, so no hidden scheduler counter or call-order convention can
shift the boundaries.

### M-004 - Loss and update order

Use unweighted `torch.nn.functional.cross_entropy` with `reduction="mean"` and
`label_smoothing=0.0` on raw `[N,10]` classifier logits and integer targets
0-9.  Each mechanics step has the order:

1. set the epoch LR;
2. clear gradients without accumulation;
3. train-mode forward;
4. mean cross-entropy;
5. backward;
6. assert all parameter gradients exist and are finite;
7. optimizer step.

Phase 3 may compute this loss only on generated tensors.  It may not compute
CIFAR predictions, accuracy, or a test-set result.

### A-010 / H-007 - Complete project RNG mapping

Continue the Phase 2 SHA256 seed-derivation rule: UTF-8 encode fields joined by
`|`, take the first eight SHA256 bytes as an unsigned big-endian integer, then
mask to 63 bits.  For each approved project master seed, use separate domains:

- `densenet-model-init-v1|MASTER_SEED` for CPU model initialization;
- `densenet-python-runtime-v1|MASTER_SEED` for Python `random`;
- `densenet-torch-cpu-runtime-v1|MASTER_SEED` for the post-initialization CPU RNG;
- `densenet-torch-cuda-runtime-v1|MASTER_SEED|DEVICE_INDEX` for each CUDA RNG;
- `densenet-loader-worker-base-v1|MASTER_SEED|EPOCH` only for DataLoader worker bootstrap.

The already-approved Phase 2 permutation and augmentation domains remain
unchanged.  Model initialization is completed under its isolated CPU seed, then
runtime CPU/CUDA states are reset to their distinct domains.  Workers still
receive explicit sample/flip/crop decisions and must not draw augmentation
randomness.  NumPy is not a formal runtime dependency; formal mechanics must
fail if hidden NumPy randomness is introduced rather than silently seeding it.

### A-011 / H-005 - No memory-saving or recomputation path

Use the validated eager, non-recomputed model graph as the only baseline:

- no gradient checkpointing or activation recomputation;
- no `torch.compile`;
- no AMP;
- no alternate memory-efficient DenseNet layer;
- no second forward of a BatchNorm-bearing segment during one update.

Phase 4 must test whether this exact graph fits batch 64.  Failure to fit does
not authorize a trajectory-changing memory path; it requires a new human
decision and equivalence package.

### A-012 / H-006 - Epoch-boundary, trajectory-preserving checkpoints

The formal design saves an immutable, hash-manifested checkpoint after every
completed training epoch and never saves or selects a best-test checkpoint.
Each checkpoint must include at least:

- schema version, completed epoch, next epoch, and project master seed;
- strict model state, including every BatchNorm buffer/counter;
- optimizer state, including all 299 momentum buffers after the first step;
- Python, PyTorch CPU, and every initialized CUDA RNG state;
- approved RNG/data/LR policy identifiers;
- source commit, environment lock hash, dataset artifact hash, and current
  configuration hash (candidate hashes in Phase 3; frozen hashes only in Phase 5);
- a manifest hash for every serialized artifact.

Writes must use a same-directory temporary file followed by atomic replacement.
Resume must fail closed on schema, hash, tensor name/shape/dtype, policy, seed,
dataset, source, environment, or configuration mismatch.

Mid-epoch resume is deliberately not retained.  If interrupted, discard the
unfinished in-memory epoch and restart it from the preceding verified
epoch-boundary checkpoint.  Because the data decisions are a pure function of
master seed and epoch, Phase 3 must prove that this rollback yields an identical
subsequent synthetic trajectory.  No test-set state or best-result field is
allowed in a formal checkpoint.

## 3. Approved Phase 3 authority

Approval permits implementation and testing of the loss, optimizer, LR
function, RNG controls, and checkpoint mechanics.  Optimizer steps are permitted
only on generated inputs/targets and must be reported as
`NON-FORMAL SYNTHETIC OPTIMIZER STEPS`.  The project-wide count of **formal
optimizer steps remains zero**.

Approval continues to prohibit:

- passing a CIFAR example through an optimizer step;
- a CIFAR training loop or partial epoch;
- validation/test predictions or accuracy;
- pretrained weights or result downloads;
- Phase 4 entry;
- Phase 5 freeze or any formal optimizer step.

## 4. Mandatory Phase 3 acceptance tests

1. Independent scalar/vector first- and subsequent-step SGD oracle, including
   coupled weight decay and Nesterov buffer state.
2. Exact optimizer configuration and one-to-one coverage of all 299 trainable
   tensors; explicit proof that BN affine tensors and classifier bias decay.
3. Independent mean-cross-entropy value and logit-gradient oracle.
4. Fail-closed epoch function tests at 1, 149, 150, 224, 225, and 300 plus
   rejection of 0 and 301.
5. Full-project generated-tensor step with finite loss, gradients, parameters,
   buffers, and optimizer state; no CIFAR read.
6. Deterministic replay for every approved master seed and every RNG domain;
   domain/epoch/device separation tests.
7. Strict checkpoint round-trip of model, optimizer, BN state, RNG state,
   cursor, policy IDs, and hashes.
8. Exact uninterrupted-versus-checkpoint-resumed multi-step synthetic trajectory
   comparison under the approved deterministic GPU policy.
9. Corruption, missing/extra key, wrong seed/config/data/source/environment,
   unsafe path, partial write, and wrong tensor metadata rejection tests.
10. A machine-readable report distinguishing synthetic optimizer steps from
    formal optimizer steps and asserting CIFAR samples, predictions, accuracy,
    pretrained downloads, and formal optimizer steps are all zero.

Passing these tests would technically validate Phase 3.  A separate human
completion decision would still be required before Phase 4.

## 5. Exact human authorization

**「我批准 Phase 3 entry decision package v1：批准 A-009 的單一參數組 PyTorch SGD 語義對應，包含 momentum 0.9、Nesterov、dampening 0、coupled weight decay 1e-4 作用於全部可訓練參數，並關閉 foreach/fused；批准 H-004 的明確 epoch learning-rate function；批准 M-004 的 mean cross-entropy 與更新順序；批准 A-010/H-007 的 SHA256 domain-separated runtime RNG mapping；批准 A-011/H-005 禁用 memory-saving、recomputation、compile 與 AMP 路徑；批准 A-012/H-006 的逐 epoch、atomic、hash-verified checkpoint 與中斷 epoch 回滾重跑規則；開始 Phase 3，但 optimizer step 僅可使用完全合成資料作為非正式 mechanics 驗證。仍禁止 CIFAR optimizer step、CIFAR 訓練、prediction、accuracy、pretrained results、Phase 4、Phase 5 freeze 與正式 optimizer step；formal optimizer steps 維持 0。」**
