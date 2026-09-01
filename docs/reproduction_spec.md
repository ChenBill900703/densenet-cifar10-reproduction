# DenseNet CIFAR Reproduction Specification - Formal Reproduction Completed

## Status and gate

- Phase: **D-057 formal runs/tests/aggregate complete; D-058 final comparison complete; D-059 professor-defense delivery complete. D-043 old run remains immutable, incomplete, abandoned, and non-resumable.**
- Formal target: **human-approved on 2026-08-16 and frozen by D-020 on 2026-08-23**.
- Approval record: exact user statement **「我批准此 DenseNet formal target」**.
- Phase 2, Phase 3, and Phase 4 records: **complete** through the exact approvals recorded in `decision_log.md`.
- Formal execution baseline: **D-046 authorized only the D-045 superseding freeze; its canonical capability and exact-account preflight passed before the final namespace was created.**
- Formal optimizer calls: **the abandoned old run contains exactly 24,421 preserved calls; each of the three accepted seeds contains exactly 234,600 calls. No old-run call contributes to a final seed or aggregate.**
- This document records the evidence-backed specification that produced the completed formal reproduction.

## 1. Verified identity

The user-supplied paper is *Densely Connected Convolutional Networks* by Gao Huang, Zhuang Liu, Laurens van der Maaten, and Kilian Q. Weinberger, arXiv:1608.06993v5, dated 2018-01-28. SHA256:

`B55AA1ADBDF07F731DAA84B94D23103D1EB22D1821A556B80212DEBEE69B096D`

The author repository is <https://github.com/liuzhuang13/DenseNet>. Phase 0 pins official snapshot candidate `6d4c8da6a1ef750c9116807b98e7c6265f51d762` (2017-08-23). This is an official, complete, post-publication runner snapshot; it is not claimed to be the authors' private experiment commit. Full identity and version differences are in `source_manifest.md`.

## 2. CIFAR candidate matrix from paper Table 2

`C10/C100` means no augmentation; `C10+/C100+` means the paper's standard augmentation. Error values are percentages. Paper parameter counts are rounded. Exact parameter counts below are derived under paper architecture semantics, no convolution biases, BN affine parameters included, and a biased classifier.

| Candidate | L | k | B | theta | Paper params | Exact params C10 / C100 (`DERIVED`) | C10 | C10+ | C100 | C100+ | Dropout | Paper result statistic / run count |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| DenseNet-40-12 | 40 | 12 | no | 1 | 1.0M | 1,019,722 / 1,060,132 | 7.00 | 5.24 | 27.55 | 24.42 | 0.2 only without augmentation; 0 with `+` | Final test evaluated once; independent-run count and aggregation `UNKNOWN` |
| DenseNet-100-12 | 100 | 12 | no | 1 | 7.0M | 6,979,642 / 7,084,852 | 5.77 | 4.10 | 23.79 | 20.20 | same | same |
| DenseNet-100-24 | 100 | 24 | no | 1 | 27.2M | 27,249,082 / 27,457,972 | 5.83 | 3.74 | 23.42 | 19.25 | same | same |
| DenseNet-BC-100-12 | 100 | 12 | yes | 0.5 | 0.8M | 769,162 / 800,032 | 5.92 | 4.51 | 24.15 | 22.27 | same | same |
| DenseNet-BC-250-24 | 250 | 24 | yes | 0.5 | 15.3M | 15,324,406 / 15,480,556 | 5.19 | 3.62 | 19.64 | 17.60 | same | same |
| DenseNet-BC-190-40 | 190 | 40 | yes | 0.5 | 25.6M | 25,624,430 / 25,821,620 | not reported | 3.46 | not reported | 17.18 | 0 on reported `+` cells | same |

Every reported Table 2 cell is a potential target, but not every cell has equally complete executable evidence. The late unified official code conflicts with the paper for basic-model initial channel count, and its custom memory layer conflicts with no-augmentation Dropout. Those limitations lower the evidence quality of basic and no-augmentation candidates.

## 3. Human-approved primary target

**Approved target:** `DenseNet-BC-100-12 / CIFAR-10+ / FP32 / batch 64 / 300 epochs`.

The human supplied the required exact approval phrase on 2026-08-16. This resolves `B-001` only. It authorizes Phase 1 architecture work, but it does not approve unresolved implementation assumptions, select seeds or reporting rules, freeze the configuration, or authorize CIFAR training.

Reasons:

- Paper and official code agree on BC architecture, `k=12`, `theta=0.5`, floor compression, three blocks, and 16 units per block.
- The official README gives this exact CIFAR-10 command shape with batch 64 and 300 epochs.
- Augmentation means dropout is 0, avoiding the custom-memory Dropout conflict.
- 769,162 exact parameters and the official 5.452 GB / 0.156 s-per-iteration Titan X anchor make it the safest evidence-complete 8 GB candidate.
- The paper error reference is **4.51%**. This is a comparison value, never a tuning target.

Possible secondary target after a successful first lifecycle: the same model on **CIFAR-100+**, paper error **22.27%**, exact parameters **800,032**. It is not approved as a formal target in the present lifecycle.

This target approval is not a freeze. Remaining BLOCKER conflicts must be resolved before Phase 5 can freeze a formal baseline and before any formal optimizer step.

## 4. Architecture semantics

### 4.1 Dense connectivity

`PAPER-SPECIFIED`, PDF p.3, Eq. (2):

`x_l = H_l([x_0, x_1, ..., x_(l-1)])`

The brackets mean feature-map concatenation, not addition. For NCHW tensors, the official Torch concatenation dimension is dimension 2 (channels): `DenseConnectLayer.lua:30-33` and custom `torch.cat(..., 2)` at `:80`.

If a block enters with `k0` channels, dense unit `l` receives `k0 + k*(l-1)` channels and adds exactly `k` new channels. Existing channels pass through unchanged by concatenation.

### 4.2 Basic, B, C, and BC

- Basic DenseNet unit: `BN -> ReLU -> 3x3 conv(k)` (`PAPER-SPECIFIED`, PDF p.3; code `DenseConnectLayer.lua:18-28` with bottleneck false).
- DenseNet-B: `BN -> ReLU -> 1x1 conv(4k) -> BN -> ReLU -> 3x3 conv(k)` (`PAPER-SPECIFIED`, PDF p.4; code `DenseConnectLayer.lua:18-28`).
- DenseNet-C: a transition maps `m` channels to `floor(theta*m)`; paper uses `theta=0.5` (`PAPER-SPECIFIED`, PDF p.4).
- DenseNet-BC: both B and C.

### 4.3 CIFAR stem, transitions, and head

- Stem: one 3x3 convolution, stride 1, padding 1. It has 16 outputs for paper basic DenseNet and `2k` for BC (`PAPER-SPECIFIED`, PDF p.4). The selected BC-100-12 therefore starts with 24 channels.
- Three equal dense blocks at spatial sizes 32x32, 16x16, 8x8.
- Two transitions: `BN -> ReLU -> 1x1 conv(stride 1, padding 0) -> 2x2 average pool(stride 2)`; if dropout is active, code places it after the transition convolution and before pooling (`models/densenet.lua:37-51`).
- After block 3: `BN -> ReLU -> 8x8 global average pooling -> reshape -> Linear` (`models/densenet.lua:42-46,82-84,129-135`).
- The code has no explicit Softmax module because `nn.CrossEntropyCriterion` supplies the softmax/log-loss computation (`models/init.lua:117`).
- Classifier bias exists (`nn.Linear` default) and is zeroed (`models/densenet.lua:160-162`).
- Convolution bias is removed when `cudnn.version >= 4000`; otherwise retained and zeroed (`models/densenet.lua:137-147`). The intended modern mapping is no convolution bias, pending freeze.

### 4.4 Depth counting - Phase 1 test obligation

The CIFAR network depth counts convolutional and classifier layers. It includes:

- 1 stem convolution;
- all dense-unit convolutions;
- 2 transition 1x1 convolutions;
- 1 final classifier.

It does not count BN, ReLU, pooling, concatenation, or dropout as layers.

For `N` dense units in each of three blocks:

- Basic DenseNet: `L = 1 + 3N + 2 + 1 = 3N + 4`.
- DenseNet-BC: each unit has two convolutions, so `L = 1 + 3*(2N) + 2 + 1 = 6N + 4`.

Official code implements `N=(depth-4)/3`, then divides by 2 for bottleneck (`models/densenet.lua:23-25`). Therefore BC-100 has `N=(100-4)/6=16` units per block and exactly `1 + 96 + 2 + 1 = 100` counted layers. A Phase 1 architecture test must independently enumerate these components.

### 4.5 BC-100-12 channel audit

`DERIVED` from the paper formula and code floor rule:

| Point | Channels |
|---|---:|
| Stem / block 1 input | 24 |
| Block 1 output (`24 + 16*12`) | 216 |
| Transition 1 output (`floor(216*0.5)`) | 108 |
| Block 2 output (`108 + 16*12`) | 300 |
| Transition 2 output (`floor(300*0.5)`) | 150 |
| Block 3 output / classifier input (`150 + 16*12`) | 342 |

Each bottleneck produces 48 intermediate channels (`4k`) and then 12 new concatenated channels.

### 4.6 Initialization

- Convolution: zero-mean normal with standard deviation `sqrt(2/(kernel_width*kernel_height*out_channels))`; this is the fan-out/backward form permitted by He et al. (`OFFICIAL-CODE-SPECIFIED`, `models/densenet.lua:137-159`; paper reference [10]).
- Convolution bias: absent for cuDNN >= 4; otherwise zero.
- BN gamma/beta: 1/0; running mean/variance: 0/1.
- Classifier bias: 0.
- Classifier weight: left at historical `nn.Linear` default, which the date-aligned candidate initializes uniformly in `[-1/sqrt(fan_in), +1/sqrt(fan_in)]` (`HISTORICAL-DEPENDENCY-BACKED`, `sources/torch-nn/Linear.lua:21-40`). For the approved target, `fan_in=342`, so the explicitly approved port interval is `[-1/sqrt(342), +1/sqrt(342)]`; the official model subsequently forces the classifier bias to zero. The exact installed Torch `nn` dependency was not pinned and the paper's wording is broad, so A-006/B-006 is a human-approved semantic port rule, not a bitwise historical claim or Phase 5 freeze.

## 5. CIFAR data protocol

### 5.1 Dataset

- CIFAR-10: 50,000 train / 10,000 test, 10 classes; CIFAR-100: 50,000 / 10,000, 100 classes (`PAPER-SPECIFIED`, PDF p.5).
- Paper holds out 5,000 training samples for validation during development, then uses all 50,000 for the final run and reports the final test error.
- Official final runner loads all 50,000 as `train` and the 10,000 test examples as `val` (`datasets/cifar10-gen.lua:49-64`, `datasets/cifar100-gen.lua:55-64`).
- The frozen sole formal dataset artifact is the Toronto CIFAR-10 binary archive, SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD`.

### 5.2 Pixel representation and normalization

Official code operates on raw 0-255 values and performs per-channel global normalization:

- CIFAR-10 mean `[125.3, 123.0, 113.9]`, std `[63.0, 62.1, 66.7]` (`datasets/cifar10.lua:37-51`).
- CIFAR-100 mean `[129.3, 124.1, 112.4]`, std `[68.2, 65.4, 70.4]` (`datasets/cifar100.lua:42-62`).
- No ZCA whitening is present in paper or official runner.

The exact train transform order is `ColorNormalize -> HorizontalFlip(p=0.5) -> RandomCrop(32,padding=4)` (`datasets/cifar10.lua:43-49`; CIFAR-100 `:54-60`). Padding is constant zero **after normalization**, so the padded border corresponds to normalized zero, not raw black. Random crop offsets are discrete integers 0 through 8 inclusive (`datasets/transforms.lua:61-83`). Test preprocessing is normalization only.

For the recommended `C10+` target, both mirroring and zero-pad/crop are active and dropout is 0. For no-augmentation cells, these augmentations must be disabled and dropout must be 0.2 after every convolution except the stem.

## 6. Training protocol

| Setting | Frozen baseline value | Evidence |
|---|---|---|
| Optimizer | SGD with Nesterov momentum | PDF p.5; `train.lua:19-29` |
| Momentum | 0.9 | PDF p.5 |
| Dampening | 0 | PDF p.5; code |
| Weight decay | `1e-4`, coupled L2 on the full flattened trainable parameter vector | PDF p.5; `train.lua:31,78`; historical `optim/sgd.lua:46-55` |
| Weight-decay scope | Conv weights, Linear weights, Linear bias, BN gamma, BN beta; conv bias only if present | `OFFICIAL-CODE-SPECIFIED` + dependency-backed derivation |
| Batch size | 64 | PDF p.5; official README command |
| Epochs | 300 | PDF p.5; official README command |
| Initial LR | 0.1 | PDF p.5 |
| LR schedule | Epochs 1-149: 0.1; 150-224: 0.01; 225-300: 0.001 | `train.lua:188-198`; `DERIVED` boundary expansion |
| Loss | multiclass cross-entropy | `models/init.lua:117` |
| Shuffle | fresh `torch.randperm(50000)` each epoch | `dataloader.lua:67-75` |
| Last batch | kept; 781 batches of 64 plus one batch of 16 (`drop_last=false`) | `dataloader.lua:63-75`; `DERIVED` |
| Updates/epoch | 782 | `DERIVED` |
| Total updates | 234,600 | `DERIVED` |
| Precision | paper-era runner default single precision | `opts.lua:28,106-113` |
| Test rule | paper: once at training end; public runner: every epoch and best test | **BLOCKER conflict C-001** |
| Seeds / run count / aggregation | `UNKNOWN` | Paper does not publish them |

Historical SGD first-step behavior includes weight decay in the gradient, then Nesterov momentum. The public runner passes all trainable tensors through a single flattened vector, so excluding BN or bias would be a protocol change.

## 7. BatchNorm historical mapping

Date-aligned cudnn.torch candidate `008c49de...` specifies:

- `eps=1e-5`;
- running-stat update coefficient `momentum=0.1` passed to cuDNN as `exponentialAverageFactor`;
- affine parameters always enabled;
- initial running mean 0 and variance 1;
- train mode uses batch statistics and updates running statistics; eval mode uses the running statistics.

Official DenseNet code then overrides affine gamma/beta to 1/0. PyTorch uses the same high-level coefficient direction (`new=(1-m)*old+m*observation`). The historical dependency candidates below determine an intended estimator-level mapping, while exact arithmetic for the authors' unpinned NVIDIA cuDNN binary remains unknown. D-008 resolves B-005 by approving the historical semantic mapping without claiming native-cuDNN bitwise identity; D-020 freezes that semantic mapping for this baseline.

The historical Torch `nn` candidate supplies a more specific semantic oracle (`sources/torch-nn/lib/THNN/generic/BatchNormalization.c:24-53`):

- training output normalizes with the biased population variance `sum((x-mean)^2)/n`;
- `running_mean = momentum*batch_mean + (1-momentum)*running_mean`;
- `running_var = momentum*(sum((x-mean)^2)/(n-1)) + (1-momentum)*running_var`, using the unbiased batch variance for the stored running value;
- evaluation normalizes with the stored running variance plus `eps`.

The date-aligned `cudnn.torch` test suite directly compares cuDNN BatchNorm with Torch `nn` for forward output, backward gradients, `running_mean`, and `running_var` (`sources/cudnn.torch/test/test.lua:640-669`). This establishes intended semantic conformance for the historical dependency candidates. It does **not** identify the authors' actual NVIDIA cuDNN build, floating-point reduction order, or bitwise trajectory. Therefore the estimator semantics are `HISTORICAL-DEPENDENCY-BACKED`, while exact native-cuDNN arithmetic remains `UNKNOWN`; B-005 is policy-resolved by D-008 and the selected semantic port is frozen by D-020.

## 8. Reporting policy evidence

The paper specifies all 50,000 training examples for the final CIFAR run and final test error at the end; it also says test errors were evaluated only once per task/model setting. It does **not** publish:

- independent run count;
- seeds;
- mean/median/best aggregation;
- variance or confidence interval.

Those quantities remain `UNKNOWN` as claims about the paper. For this reproduction, the human separately approved and later froze three preregistered project seeds (`1021082110`, `1747066946`, `869460408`), reporting every run, arithmetic mean as primary, and sample standard deviation as descriptive. These are `IMPLEMENTATION-ASSUMPTION` policies, not paper seeds/statistics. The post-publication runner's best-test behavior is preserved as conflict `C-001`; the frozen reproduction instead performs one test after epoch 300.

## 9. Completed result and preservation rule

The three single final-test errors are 4.66%, 4.61%, and 4.81%. The frozen mean is 4.693333333333% with sample SD 0.104083299973 percentage points. The paper reference is 4.51%, giving a transparent +0.183333333333 pp difference. See `docs/final_reproduction_report.md` and `docs/final_evidence_index.md`.

Preserve every formal result, ledger, checkpoint, manifest, decision artifact, older tag, D-028 file, and D-043 abandoned artifact. Any future experiment is a new lifecycle and must not overwrite, reinterpret, or selectively combine these results.
