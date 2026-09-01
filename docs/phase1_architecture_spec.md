# Phase 1 Architecture Specification

## 1. Status, authority, and boundary

- Lifecycle: **PHASE 1 TECHNICALLY VALIDATED ON 2026-08-16 - HOLD BEFORE PHASE 2**.
- Human approval record: on 2026-08-16 the user stated exactly **「我批准此 DenseNet formal target」**.
- Approved target: **DenseNet-BC-100-12 / CIFAR-10+ / FP32 / batch 64 / 300 epochs**.
- Approval effect: target-selection blocker `B-001` is resolved.
- Freeze state: **NOT PHASE 5 FROZEN**.
- Formal optimizer steps executed: **0**.

Phase 1 may implement the model and run architecture, initialization, BatchNorm, synthetic forward, and synthetic backward tests. It must not implement a DataLoader, optimizer, or scheduler; download pretrained results; train on CIFAR; measure accuracy; or execute any formal optimizer step.

## 2. Evidence basis

The following order governs this specification:

1. user-supplied paper PDF, SHA256 `B55AA1ADBDF07F731DAA84B94D23103D1EB22D1821A556B80212DEBEE69B096D`;
2. official DenseNet repository snapshot `6d4c8da6a1ef750c9116807b98e7c6265f51d762`;
3. historical dependency candidates recorded in `source_manifest.md`;
4. arithmetic derived from those sources;
5. explicitly approved implementation assumptions.

No Phase 1 test result is a `FORMAL-REPRODUCTION-RESULT`. Passing synthetic tests validates the port's implementation against this specification; it does not reproduce the paper's error rate.

## 3. Exact architecture contract

### 3.1 Input and output

| Contract | Value | Evidence class |
|---|---|---|
| Input layout | NCHW | `OFFICIAL-CODE-SPECIFIED` + `IMPLEMENTATION-ASSUMPTION` for Torch-to-PyTorch dimension numbering |
| Input channels | 3 | `PAPER-SPECIFIED` / CIFAR definition |
| Input spatial size | 32 x 32 | `PAPER-SPECIFIED` |
| Output | unnormalized logits with shape `N x 10` | `OFFICIAL-CODE-SPECIFIED` |
| Explicit Softmax module | none | `OFFICIAL-CODE-SPECIFIED`; historical cross-entropy supplies it |

The Phase 1 implementation should reject incompatible channel or spatial shapes explicitly so an accidental ImageNet-style input cannot silently pass.

### 3.2 Stem and dense blocks

| Component | Exact contract | Evidence class |
|---|---|---|
| Stem | 3x3 convolution, 3 -> 24 channels, stride 1, padding 1, no bias in the Phase 1 port | shape is `PAPER-SPECIFIED` + `OFFICIAL-CODE-SPECIFIED`; bias removal is the official code's cuDNN >= 4 branch plus a `DERIVED` modern-path mapping, not a paper claim |
| Dense blocks | 3 equal blocks | `PAPER-SPECIFIED` |
| Units per block | 16 | `DERIVED` from `L=6N+4`, `L=100` |
| Unit bottleneck | BN -> ReLU -> 1x1 conv with 48 outputs | `PAPER-SPECIFIED` + `OFFICIAL-CODE-SPECIFIED` |
| Unit composite | BN -> ReLU -> 3x3 conv with 12 outputs, padding 1 | `PAPER-SPECIFIED` + `OFFICIAL-CODE-SPECIFIED` |
| Dense connection | concatenate the unchanged input channels and 12 new channels along NCHW dimension 1 | `PAPER-SPECIFIED` + `OFFICIAL-CODE-SPECIFIED` |
| Dropout | absent / probability 0 for CIFAR-10+ | `PAPER-SPECIFIED` + `OFFICIAL-CODE-SPECIFIED` |

Every dense unit therefore adds exactly 12 channels; it must not add tensors elementwise or overwrite earlier feature maps.

### 3.3 Transitions and head

| Component | Exact contract | Evidence class |
|---|---|---|
| Transition 1 | BN -> ReLU -> 1x1 conv 216 -> 108, no bias in the Phase 1 port -> 2x2 average pool, stride 2 | order is `OFFICIAL-CODE-SPECIFIED`; widths are `DERIVED`; bias removal follows the official cuDNN >= 4 branch; paper does not alone fix ReLU position or convolution bias |
| Transition 2 | BN -> ReLU -> 1x1 conv 300 -> 150, no bias in the Phase 1 port -> 2x2 average pool, stride 2 | order is `OFFICIAL-CODE-SPECIFIED`; widths are `DERIVED`; bias removal follows the official cuDNN >= 4 branch; paper does not alone fix ReLU position or convolution bias |
| Compression | `floor(0.5*m)` | `PAPER-SPECIFIED` + `OFFICIAL-CODE-SPECIFIED` |
| Head | BN -> ReLU -> fixed 8x8 average pool -> flatten -> Linear(342,10) | `OFFICIAL-CODE-SPECIFIED` + `DERIVED` |
| Classifier bias | present and explicitly zero | `OFFICIAL-CODE-SPECIFIED` |

The 8x8 pool is a fixed architectural consequence of the approved 32x32 CIFAR input and two 2x downsamplings. Replacing it with an adaptive pool would be a port design change and is not part of this contract.

The official initializer removes every convolution bias only when `cudnn.version >= 4000`; otherwise it retains and zeros those biases. The Phase 1 no-bias contract deliberately follows that official modern-cuDNN branch and is `OFFICIAL-CODE-SPECIFIED` + `DERIVED`, not `PAPER-SPECIFIED`. The exact author-installed cuDNN build remains unpinned, so the branch choice must stay visible at Phase 5 even though the Phase 1 parameter oracle uses no convolution biases.

## 4. Independent depth and channel ledger

### 4.1 Counted depth

`DERIVED`:

| Counted layer class | Count |
|---|---:|
| Stem convolution | 1 |
| Dense-unit convolutions (`3 blocks * 16 units * 2`) | 96 |
| Transition convolutions | 2 |
| Final classifier | 1 |
| **Total depth** | **100** |

BatchNorm, ReLU, pooling, concatenation, and dropout are not counted in paper depth. The resulting module inventory additionally contains 99 BatchNorm operations, 48 dense concatenations, two transition pools, and one final pool.

### 4.2 Channel and spatial trace

`DERIVED`:

| Point | Shape excluding batch |
|---|---|
| Input | 3 x 32 x 32 |
| Stem / block 1 input | 24 x 32 x 32 |
| Block 1 output | 216 x 32 x 32 |
| Transition 1 output | 108 x 16 x 16 |
| Block 2 output | 300 x 16 x 16 |
| Transition 2 output | 150 x 8 x 8 |
| Block 3 output | 342 x 8 x 8 |
| Fixed average-pool output | 342 x 1 x 1 |
| Classifier output | 10 |

## 5. Independent parameter-count ledger

All values below are `DERIVED` from the specified shapes, no convolution bias, affine BatchNorm, and a biased 10-class classifier.

| Stage | Trainable parameters |
|---|---:|
| Stem convolution | 648 |
| Dense block 1 | 175,680 |
| Transition 1 | 23,760 |
| Dense block 2 | 242,880 |
| Transition 2 | 45,600 |
| Dense block 3 | 276,480 |
| Final BatchNorm | 684 |
| Linear classifier | 3,430 |
| **Total** | **769,162** |

An orthogonal tensor-class check is 741,744 convolution weights + 23,988 BatchNorm affine parameters + 3,430 classifier parameters = 769,162. The Phase 1 implementation must independently enumerate trainable tensors and match 769,162 exactly. A rounded paper value of 0.8M is not an acceptable test oracle. Accidentally enabling every convolution bias would add 3,162 parameters and produce 772,324; that total is a useful failure sentinel, not an alternate valid model.

## 6. Initialization contract and evidence boundary

| Tensor class | Phase 1 contract | Evidence class / boundary |
|---|---|---|
| Convolution weight | normal mean 0, standard deviation `sqrt(2/(kernel_width*kernel_height*out_channels))` | `OFFICIAL-CODE-SPECIFIED` |
| Convolution bias | absent | `OFFICIAL-CODE-SPECIFIED` for cuDNN >= 4 mapping |
| BN affine weight/bias | 1 / 0 | `OFFICIAL-CODE-SPECIFIED` |
| BN running mean/variance | 0 / 1 | `HISTORICAL-DEPENDENCY-BACKED` |
| Classifier weight | explicit uniform `[-1/sqrt(342), +1/sqrt(342)]` proposed for the port | `HISTORICAL-DEPENDENCY-BACKED`; unapproved at this Phase 1 record, later approved by D-008, still not Phase 5 frozen |
| Classifier bias | 0 | `OFFICIAL-CODE-SPECIFIED` |

The classifier rule is suitable as a Phase 1 test oracle for the evidence-backed candidate port, but passing that test does not convert the unpinned dependency candidate into proof of the authors' exact installed `nn` version. Formal-freeze adoption requires the recorded human decision in A-006/B-006.

Torch7 and modern PyTorch consume constructor random numbers through different module traversal and random-number generators. Consequently, matching the initialization distributions does not establish tensor-level equality to an unknown paper seed. Phase 5 may freeze only a **project seed -> project initial-state hash** relationship, labelled as project provenance; it must never be described as a paper-seed reconstruction.

## 7. BatchNorm semantic oracle and residual unknown

The date-aligned Torch `nn` source gives the following `HISTORICAL-DEPENDENCY-BACKED` training behavior:

- batch mean: `sum(x)/n`;
- normalization variance: `sum((x-mean)^2)/n`;
- saved running-variance observation: `sum((x-mean)^2)/(n-1)`;
- update direction: `new = momentum*observation + (1-momentum)*old` with `momentum=0.1`;
- evaluation variance: stored `running_var`, with `eps=1e-5` inside the square root.

The date-aligned cudnn.torch tests compare the cuDNN implementation against Torch `nn` for forward output, backward gradient, running mean, and running variance. This supports semantic conformance, not bitwise identity. The authors' actual cuDNN binary, algorithm choice, parallel reduction order, and exact floating-point trajectory are `UNKNOWN`; Phase 1 must not claim otherwise.

Modern PyTorch also stores a `num_batches_tracked` BatchNorm buffer that is absent from the cited historical state. Under a fixed momentum of 0.1 it should not enter the update formula, but its existence and checkpoint value must be recorded as an `IMPLEMENTATION-ASSUMPTION` detail. Any checkpoint/recomputation path that could execute a BatchNorm forward twice and update running state twice is forbidden for the baseline unless a separate equivalence test proves identical logits, gradients, and BN state.

## 8. Mandatory Phase 1 tests

The following validation obligations are implemented and passed; the exact observed record is in `verification_phase1.md`:

1. enumerate 100 counted layers and 16 dense units per block;
2. verify the full spatial/channel trace and that each concatenation preserves its input prefix unchanged;
3. verify all convolutions are bias-free and the classifier alone has its specified bias;
4. count exactly 769,162 trainable parameters;
5. verify no dropout module is active for the approved augmented target;
6. verify fixed 8x8 final pooling and `N x 10` logits;
7. verify initialization formulas and deterministic model construction under a test-only seed;
8. verify BatchNorm biased forward variance, unbiased running-variance update, momentum direction, initial state, and evaluation state against an analytic tensor oracle;
9. run finite synthetic forward and cross-entropy backward checks and verify every trainable parameter receives a finite gradient;
10. run a double-precision gradient/reference check on a small dense unit;
11. compare the complete formal graph in train and eval modes against an independently traversed functional oracle, requiring exact logits, BatchNorm state, input gradients, and all 299 parameter gradients;
12. save and reload a Phase 1 state and require identical logits and all BatchNorm buffers;
13. execute **no optimizer step** and report synthetic checks only as Phase 1 validation.

## 9. Phase 1 exit gate

The original mandatory suite passed 27/27 in the pinned Phase 1 environment. A superseding correctness-maintenance audit expanded the suite to 47 tests and added train/eval execution-level and environment/evidence-integrity oracles. Both the project environment and a final freshly reconstructed external environment passed 47/47. Independent code/specification re-audit found no remaining architecture or model-math discrepancy after its findings were corrected. The Phase 1 technical criterion is therefore met.

Phase 1 completion does not authorize CIFAR data work or formal training by itself. The project is held before Phase 2 under the repository blocker rule. The paper-versus-public-runner test-cadence conflict `C-001`, seeds/aggregation, determinism, BatchNorm port adoption, classifier port adoption, dataset hashes, artifact hashes, and later phase validations must still be resolved before Phase 5.
