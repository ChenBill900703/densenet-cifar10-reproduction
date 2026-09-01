# DenseNet-BC-100-12 on CIFAR-10+: Final Reproduction Report

Status date: **2026-08-28**  
Target: **DenseNet-BC-100-12 / CIFAR-10+ / FP32 / batch 64 / 300 epochs**

## 1. Executive conclusion

This project completed three preregistered, fixed-baseline training runs and exactly one final-test evaluation per run. The observed errors were **4.66%**, **4.61%**, and **4.81%**. The frozen arithmetic mean is **4.693333333333%** and the descriptive sample standard deviation is **0.104083299973 percentage points**.

The locked arXiv-v5 paper reports **4.51%** for DenseNet-BC, depth 100, growth rate 12, CIFAR-10 with standard augmentation. The reproduction mean is therefore **0.183333333333 percentage points higher** than the paper value. This is a close numerical reproduction of the paper's performance range, but it is not a bit-identical result and it is not evidence of statistical equivalence. The paper does not publish the seed, independent-run count, variance, or aggregation rule for this table cell, so no post-hoc pass tolerance is introduced.

Evidence classification:

- Paper value 4.51%: `PAPER-SPECIFIED`.
- Per-seed results and frozen aggregate: `FORMAL-REPRODUCTION-RESULT`.
- Three project seeds, arithmetic mean, and sample SD: approved `IMPLEMENTATION-ASSUMPTION`, fixed before formal execution.
- Exact equality to the authors' paper-era cuDNN trajectory: `UNKNOWN`.

## 2. Primary evidence and target identity

The primary paper is *Densely Connected Convolutional Networks* by Gao Huang, Zhuang Liu, Laurens van der Maaten, and Kilian Q. Weinberger, arXiv:1608.06993v5. Its local SHA256 is:

`B55AA1ADBDF07F731DAA84B94D23103D1EB22D1821A556B80212DEBEE69B096D`

The paper's Table 2 reports the selected target as:

| Model | Depth | Growth rate | Params | Dataset | Paper error |
|---|---:|---:|---:|---|---:|
| DenseNet-BC | 100 | 12 | 0.8M rounded | CIFAR-10+ | 4.51% |

The author-controlled repository is `https://github.com/liuzhuang13/DenseNet.git`, pinned at official snapshot `6d4c8da6a1ef750c9116807b98e7c6265f51d762`. It is treated as a complete post-publication official snapshot, not falsely described as the private commit that produced Table 2.

## 3. What was reproduced

### 3.1 Architecture

The implementation follows the paper and official code semantics:

- Dense connectivity: `x_l = H_l([x_0, x_1, ..., x_(l-1)])`; brackets are channel concatenation, not addition.
- DenseNet-B unit: `BN -> ReLU -> 1x1 conv(4k) -> BN -> ReLU -> 3x3 conv(k)`.
- DenseNet-C transition: channels become `floor(theta*m)` with `theta=0.5`.
- Three dense blocks, 16 bottleneck units per block, and depth accounting `L=6N+4=100`.
- Channel path: `24 -> 216 -> 108 -> 300 -> 150 -> 342`.
- Final head: `BN -> ReLU -> global average pool -> Linear(342,10)`.
- Exact trainable parameter count: **769,162**.

DenseNet concatenates all earlier features, so each layer can reuse low- and high-level representations directly. ResNet instead adds a residual branch to an identity path; addition keeps width fixed, while DenseNet concatenation increases the feature collection by the growth rate `k` at every dense unit.

### 3.2 Data and optimization protocol

The frozen protocol used:

- Approved Toronto CIFAR-10 binary archive SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD`.
- All 50,000 training records and 10,000 final-test records.
- Raw-255 normalization constants: mean `[125.3,123.0,113.9]`, std `[63.0,62.1,66.7]`.
- Training transform order: normalize, horizontal flip with probability 0.5, normalized-zero pad 4, random 32x32 crop with offsets 0–8.
- FP32 physical batch 64, workers 2, no AMP, no TF32, no compile, no accumulation, and deterministic algorithms enabled.
- Mean cross-entropy from raw logits.
- SGD, Nesterov momentum 0.9, dampening 0, coupled weight decay `1e-4` on all trainable parameters.
- Learning rate 0.1 for epochs 1–149, 0.01 for 150–224, and 0.001 for 225–300.
- 782 updates per epoch and exactly 234,600 accepted updates per seed.
- One sequential final-test evaluation per seed only after all three epoch-300 training artifacts passed hash verification.

## 4. Formal execution controls

The runnable baseline was frozen before the first accepted optimizer call. Its controlling identities include:

- Freeze manifest SHA256: `6CC22F7D918DF1689C4E14A33E8BB4FDAF502EF51149AF1E6537D2618547EC26`.
- Source commit: `863375d4082abaa2a7f6580e4f90c3ec114cbce3`.
- Canonical config SHA256: `C5F1B2DA0B2E0A5476531C0460313849EEB4058400BED0E0EFC3227D82A83213`.
- Project wheel SHA256: `D31FE8A0DFBDBF4B4100C28E587DDDA98A13EE63219B373143DF41C01F8CE859`.
- Installed environment manifest SHA256: `1E0D0EA18AE43BCBEDA2962EB363C7D8CE7FBB8B2B03000D33A8BEA130A7C953`.
- GPU: NVIDIA GeForce RTX 3070 Ti, compute capability 8.6.

Every optimizer call was surrounded by an append-only intent/completion hash-chain ledger. Every completed epoch produced an atomic checkpoint and a SHA256-bound manifest. The final namespace retained 300 checkpoints for each seed. Each seed ended with 234,600 intents, 234,600 completions, zero unresolved intents, 234,600 finite progress records, and 300 valid checkpoint manifests.

## 5. Corrective history and why it does not contaminate the result

Three execution problems were exposed and corrected before the final three-run result was accepted:

1. Prepared-directory ACL access was not checked early enough. The first attempt failed before decoded samples, optimizer calls, checkpoints, or predictions. Its two zero-byte files remain immutable evidence.
2. A later old run stopped for an unknown reason and was resumed once under an approved epoch-boundary rollback. It was subsequently abandoned when a ledger-performance problem was found.
3. The old ledger implementation rescanned the full ledger after every append, producing quadratic overhead. That namespace was deliberately stopped, frozen as incomplete/non-resumable, and never merged with the final runs. The corrected implementation performs a complete verification at open/restart and equivalent incremental validation for new records.

The abandoned namespace's 24,421 physical calls remain preserved but are not part of any seed, checkpoint, test result, or aggregate reported here. All final seeds restarted from epoch 1 in a new full-manifest-hash namespace under the superseding freeze.

## 6. Formal results

| Fixed order | Project seed | Incorrect / 10,000 | Error | Epoch-300 checkpoint SHA256 |
|---:|---:|---:|---:|---|
| 1 | 1021082110 | 466 | 4.66% | `5E5197F5D75E3D5CDE9C2CED5FCCBB0C2948965B67E7FDAFF99BB9DECBDF4811` |
| 2 | 1747066946 | 461 | 4.61% | `FF8180B8FC1B147E6CA91BDEEB5BB449D37D5E133505CBC8B3AC779353531387` |
| 3 | 869460408 | 481 | 4.81% | `EC466CFD49C9C732EA94F92AD3D8A7C2DC252DD2BD300852A5DF62A68371C0A8` |

Frozen aggregate:

- Exact mean: `352/75%`.
- Decimal mean: **4.693333333333%**.
- Sample standard deviation: **0.104083299973 percentage points**.
- Selection: **none**.
- Aggregate SHA256: `A2669C814149C11101B9963B7FC6F24248EE80BAA674D8721628A80166F6D46A`.

## 7. Comparison with the paper

| Quantity | Value | Evidence class |
|---|---:|---|
| Paper DenseNet-BC-100-12 C10+ error | 4.51% | `PAPER-SPECIFIED` |
| Reproduction seed 1 | 4.66% | `FORMAL-REPRODUCTION-RESULT` |
| Reproduction seed 2 | 4.61% | `FORMAL-REPRODUCTION-RESULT` |
| Reproduction seed 3 | 4.81% | `FORMAL-REPRODUCTION-RESULT` |
| Reproduction mean | 4.693333333333% | `FORMAL-REPRODUCTION-RESULT` |
| Absolute mean difference | +0.183333333333 pp | `DERIVED` |

The defensible conclusion is:

> The formal reproduction is numerically close to the paper: all three fixed runs achieved 4.61%–4.81% error and the preregistered mean was 4.69%, 0.18 percentage points above the reported 4.51%. The result supports the paper's central performance claim for this configuration, but exact or statistical equivalence cannot be asserted because the paper does not disclose seeds, run count, aggregation, variance, or the exact paper-era cuDNN environment.

No seed was selected, no best epoch was used, no test-guided tuning occurred, and no tolerance was invented after observing the result.

## 8. Remaining limitations

- The authors' exact training seed and independent-run count are unknown.
- The authors' exact NVIDIA cuDNN build and floating-point reduction order are unknown.
- PyTorch reproduces the evidence-backed semantics, but it is not a bitwise re-execution of Torch7/cuDNN.
- Deterministic IEEE-FP32 execution was an approved project policy; the public repository's `fastest` path is not deterministic.
- The paper value and the reproduction mean are different statistics because the paper does not disclose whether 4.51% is one run, an aggregate, or a selected result.

These limitations constrain the strength of the equality claim; they do not invalidate the executed protocol or the stored results.

## 9. Final disposition

**Completed formal reproduction.** The target architecture, dataset, optimization protocol, three preregistered runs, one-time final tests, and frozen aggregation all completed with hash-verified artifacts. The project reproduced the paper's DenseNet-BC-100-12/CIFAR-10+ performance closely, with a transparent +0.18 pp difference and no post-hoc intervention.

