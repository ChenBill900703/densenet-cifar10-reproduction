# Evidence Table - Phase 3 Completed

Confidence describes the claim supported by the cited source, not confidence that the source equals the authors' unrecorded private environment.

Lifecycle note: the human approved `DenseNet-BC-100-12 / CIFAR-10+ / FP32 / batch 64 / 300 epochs` and completed Phases 1-5. D-020 formally froze the validated baseline. Phase 6 and formal training authority remain absent.

| Setting | Evidence class | Source and exact location | Interpretation | Confidence | Conflict / caveat |
|---|---|---|---|---|---|
| Paper identity | `PAPER-SPECIFIED` | User PDF p.1; arXiv record | arXiv:1608.06993v5, four named authors | High | v5 postdates CVPR publication |
| Dense connectivity | `PAPER-SPECIFIED` | PDF p.3 Eq. (2) | Every dense unit consumes concatenated preceding features | High | None |
| Concatenation axis | `OFFICIAL-CODE-SPECIFIED` | `models/DenseConnectLayer.lua:30-33,80` | Channel dimension (Torch dimension 2) | High | Port maps to PyTorch dim 1 for NCHW |
| Growth rate | `PAPER-SPECIFIED` | PDF p.3, Growth rate | Each unit adds exactly `k` feature maps; input grows by `k` per unit | High | None |
| Basic unit order | `PAPER-SPECIFIED` + `OFFICIAL-CODE-SPECIFIED` | PDF p.3; `DenseConnectLayer.lua:18-28` | BN-ReLU-3x3 conv | High | None |
| BC unit order | `PAPER-SPECIFIED` + `OFFICIAL-CODE-SPECIFIED` | PDF p.4; `DenseConnectLayer.lua:18-28` | BN-ReLU-1x1-BN-ReLU-3x3 | High | None for dropout 0 |
| Bottleneck width | `PAPER-SPECIFIED` | PDF p.4 | `4k` | High | None |
| Compression | `PAPER-SPECIFIED` | PDF p.4 | `theta=0.5` for C/BC experiments | High | None |
| Compression rounding | `PAPER-SPECIFIED` + `OFFICIAL-CODE-SPECIFIED` | PDF p.4; `models/densenet.lua:74-80` | Floor | High | None |
| CIFAR block count | `PAPER-SPECIFIED` | PDF p.4 | Three equal dense blocks | High | None |
| Basic initial channels | `PAPER-SPECIFIED` + earliest official code | PDF p.4; commit `cbb6bff...`, `densenet.lua:19-21` | 16 | High | Late unified code uses `2k`; C-003 |
| BC initial channels | `PAPER-SPECIFIED` + `OFFICIAL-CODE-SPECIFIED` | PDF p.4; `models/densenet.lua:14-15,67-70` | `2k` | High | None |
| Stem convolution | `OFFICIAL-CODE-SPECIFIED` | `models/densenet.lua:67-70` | 3x3, stride 1, padding 1 | High | Conv bias version-conditional |
| Transition order | `PAPER-SPECIFIED` + `OFFICIAL-CODE-SPECIFIED` | PDF pp.3-4; `models/densenet.lua:37-51` | BN-ReLU-1x1 conv-(dropout)-2x2 avg pool | High | Paper text omits explicit ReLU but table convention/code clarify it |
| Final head order | `OFFICIAL-CODE-SPECIFIED` | `models/densenet.lua:42-46,82-84,129-135` | BN-ReLU-global avg pool-Linear | High | Paper states global average + softmax classifier |
| Depth formula | `OFFICIAL-CODE-SPECIFIED` + `DERIVED` | `models/densenet.lua:23-25` | Basic `3N+4`; BC `6N+4`; stem, two transitions, classifier counted | High | Requires Phase 1 enumeration test |
| BC-100 units/block | `DERIVED` | Depth formula | 16 | High | None |
| BC-100 channel sequence | `DERIVED` | Growth/compression rules | 24 -> 216 -> 108 -> 300 -> 150 -> 342 | High | None |
| BC-100 exact C10 params | `DERIVED` | Architecture + bias rules | 769,162 | High | Must be rechecked by Phase 1 code |
| Convolution padding | `PAPER-SPECIFIED` + code | PDF p.4; `DenseConnectLayer.lua:21,27`; `models/densenet.lua:48,70` | 3x3 pad 1; 1x1 pad 0 | High | None |
| Convolution bias | `OFFICIAL-CODE-SPECIFIED` | `models/densenet.lua:137-147` | Removed for cuDNN >= 4, else zero | High | Exact author cuDNN build unpinned |
| Classifier bias | `OFFICIAL-CODE-SPECIFIED` + dependency | `models/densenet.lua:160-162`; `torch-nn/Linear.lua:3-12` | Present and zero initialized | High | None under candidate |
| Conv initialization | `OFFICIAL-CODE-SPECIFIED` | `models/densenet.lua:137-159` | Normal mean 0, std `sqrt(2/fan_out)` | High | Paper only cites He et al. generally |
| Classifier weight init | `HISTORICAL-DEPENDENCY-BACKED` | `torch-nn/Linear.lua:21-40` | Historical candidate uses uniform `±1/sqrt(fan_in)`; approved target has `fan_in=342` | Medium | A-006/B-006 approved and frozen by D-020; exact installed historical nn version remains unpinned |
| BN affine init | `OFFICIAL-CODE-SPECIFIED` | `models/densenet.lua:151-159` | gamma 1, beta 0 | High | None |
| BN defaults | `HISTORICAL-DEPENDENCY-BACKED` | `cudnn.torch/BatchNormalization.lua:9-40` | eps 1e-5, coefficient 0.1, affine, running 0/1 | Medium-high | Exact author-installed cudnn.torch/cuDNN versions unpinned |
| BN training/running-variance semantics | `HISTORICAL-DEPENDENCY-BACKED` | `torch-nn/lib/THNN/generic/BatchNormalization.c:24-53`; `cudnn.torch/test/test.lua:640-669` | Forward uses biased variance (`/n`); running variance uses unbiased variance (`/(n-1)`); cuDNN wrapper is tested for conformance with Torch nn outputs, gradients, and running state | Medium-high | A-005/B-005 semantic rule approved; actual cuDNN build, reduction order, and bitwise arithmetic remain `UNKNOWN` |
| CIFAR sizes | `PAPER-SPECIFIED` | PDF p.5, section 4.1 | 50k train / 10k test | High | Paper also uses 5k validation during development |
| Final train size | `PAPER-SPECIFIED` | PDF p.5 | All 50k for final run | High | Runner uses all 50k by construction |
| Historical CIFAR-10 source | `OFFICIAL-CODE-SPECIFIED` | `datasets/cifar10-gen.lua:11-16,43-64` | Torch-hosted converted CIFAR-10 archive | High | Endpoint returned HTTP 403; bytes/hash/equivalence remain `UNKNOWN` |
| Toronto CIFAR-10 artifacts | `DERIVED` + `IMPLEMENTATION-ASSUMPTION` | Dataset-author downloads; `evidence/cifar10-artifacts.json`; Phase 2 diagnostic; D-010; D-020 | Python SHA256 `6D958B...001CE`, binary SHA256 `C4A38C...CA1DD`; all 60,000 label/pixel records byte-exact across formats | High for measured identity/equivalence | Binary is the frozen sole formal artifact; Python is equivalence evidence only; metadata differs by one terminal blank line |
| CIFAR-100 source | `OFFICIAL-CODE-SPECIFIED` | `datasets/cifar100-gen.lua:10-18,49-64` | Toronto CIFAR-100 binary archive | High | Formal archive hash not yet recorded |
| Pixel scale | `OFFICIAL-CODE-SPECIFIED` | `datasets/cifar10.lua:23-31,37-41` | Raw 0-255 before normalization | High | No `/255` in CIFAR path |
| C10 normalization | `OFFICIAL-CODE-SPECIFIED` | `datasets/cifar10.lua:37-51` | Channel means/std `[125.3,123.0,113.9]` / `[63.0,62.1,66.7]` | High | Constants rounded to one decimal |
| C100 normalization | `OFFICIAL-CODE-SPECIFIED` | `datasets/cifar100.lua:42-62` | `[129.3,124.1,112.4]` / `[68.2,65.4,70.4]` | High | Constants rounded to one decimal |
| Augmentation | `PAPER-SPECIFIED` + code | PDF p.5; `datasets/cifar10.lua:43-49` | Normalize, p=0.5 horizontal flip, 4-pixel zero pad, random 32 crop | High | Padding happens after normalization |
| Crop semantics | `OFFICIAL-CODE-SPECIFIED` | `datasets/transforms.lua:61-83` | Constant-zero padding; integer x/y offsets 0..8 | High | None |
| Test preprocessing | `OFFICIAL-CODE-SPECIFIED` | `datasets/cifar10.lua:50-52` | Normalize only | High | None |
| ZCA | `OFFICIAL-CODE-SPECIFIED` absence | CIFAR dataset/transform files | Not used | High | Paper does not mention ZCA |
| Dropout condition | `PAPER-SPECIFIED` | PDF pp.5-6 | Only no-augmentation C10/C100/SVHN; p=0.2 after all conv except stem | High | Custom memory mode omits dropout; C-004 |
| Dropout train/eval math | `HISTORICAL-DEPENDENCY-BACKED` | `torch-nn/Dropout.lua:17-53` | Inverted dropout during train; identity during eval | High for candidate | Exact installed dependency unpinned |
| Optimizer | `PAPER-SPECIFIED` + code | PDF p.5; `train.lua:19-29,78` | SGD, Nesterov, momentum .9, dampening 0 | High | None |
| Weight decay value | `PAPER-SPECIFIED` | PDF p.5 | `1e-4` | High | None |
| Weight decay scope/math | `OFFICIAL-CODE-SPECIFIED` + dependency | `train.lua:31`; `torch-optim/sgd.lua:43-55` | Coupled L2 on the entire flattened parameter vector | High | Do not exclude BN/bias |
| Batch size | `PAPER-SPECIFIED` | PDF p.5 | 64 | High | Code defaults 32 unless explicit; C-002 |
| Epochs | `PAPER-SPECIFIED` | PDF p.5 | 300 | High | Code defaults 164 unless explicit; C-002 |
| LR | `PAPER-SPECIFIED` + code | PDF p.5; `train.lua:188-198` | .1, divide by 10 at epochs 150 and 225 | High | Freeze call order to avoid off-by-one |
| Shuffle | `OFFICIAL-CODE-SPECIFIED` + `IMPLEMENTATION-ASSUMPTION` | `dataloader.lua:67-75`; D-010; D-020 | New random permutation each epoch; project uses the frozen `densenet-cifar10-loader-v1` mapping and two training workers | High | Historical thread scheduling is unrecoverable; the project mapping is frozen rather than claimed as historical identity |
| Drop last | `OFFICIAL-CODE-SPECIFIED` | `dataloader.lua:63-75` | False; keep final 16 samples | High | None |
| Loss | `OFFICIAL-CODE-SPECIFIED` | `models/init.lua:117` | Cross entropy | High | None |
| Seed | `UNKNOWN` for paper; project policy frozen | Paper silent; `opts.lua:23`, `main.lua:25-27`; D-008; D-010; D-020 | Paper seeds unknown; three SHA256-derived project seeds and their data-stream mapping are frozen | High confidence in paper unknown and project decision | Does not convert project seeds into paper seeds |
| Independent run count | `UNKNOWN` | PDF pp.5-6 | Not stated | High confidence in unknown | “evaluated once” describes test cadence, not clearly run count |
| Reporting selection | `PAPER-SPECIFIED` vs official-code conflict | PDF pp.5-6; `main.lua:50-68`; D-008 | Paper final once; code every epoch/best; project selected paper-faithful epoch-300 one-time test | High | C-001 policy resolved for current target; conflict remains documented |
| Checkpoint schema | `OFFICIAL-CODE-SPECIFIED` | `checkpoints.lua:27-67` | Epoch model/optimizer plus latest pointer; best model saved | High | Does not save RNG/data cursor; insufficient for project governance |
| Official command for BC100 C10 | `OFFICIAL-CODE-SPECIFIED` | `README.md:72-75` | batch64, 300 epochs, depth100, k12 | High | Other critical defaults must still be made explicit |
| PyTorch as Phase 1 framework | `IMPLEMENTATION-ASSUMPTION` | User project requirement | Modern-framework port, not a claim about the paper-era framework | High | Target approval does not by itself freeze detailed translation assumptions |
