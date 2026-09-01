# Phase 0 Source Manifest

Status: **source identities locked; exact user PDF restored and committed; Phases 1-5 complete; D-024 corrective formal freeze is the superseding baseline; first D-020 freeze preserved as history; D-025 Phase 6 entry approved and D-027 exact live preflight passed at formal optimizer steps 0**. Timestamps are source timestamps, not claims about the authors' private experiment environment.

Machine-verifiable identity is committed in `evidence/source-lock.json` and checked by `scripts/verify_sources.py`. The check covers file hashes; repository pins, remotes, and locked default remote heads; every chronology commit cited by this project; non-shallow/non-partial required history with no missing reachable objects; detached HEADs; untracked files and other worktree changes; pin ancestry; and Git object integrity. This deliberately claims completeness only for the evidence-relevant locked refs/commits, not for every ref that may ever have existed on the remote. The exact user-supplied PDF is now committed at its locked relative path, while the five forensic clones remain host-bound inputs outside the root Git tree. The task-specific `DENSENET_USER_PAPER_PATH` environment override remains available for checking another copy with the same SHA256.

## Primary paper supplied by the user

| Field | Verified value |
|---|---|
| File | `docs/1608.06993v5.pdf` (restored by the user on 2026-08-23; byte identity matches the original lock) |
| Title | *Densely Connected Convolutional Networks* |
| Authors | Gao Huang, Zhuang Liu, Laurens van der Maaten, Kilian Q. Weinberger |
| Identifier | arXiv:1608.06993v5 `[cs.CV]` |
| Version date printed in PDF | 2018-01-28 |
| Pages | 9 |
| File size | 1,142,400 bytes |
| SHA256 | `B55AA1ADBDF07F731DAA84B94D23103D1EB22D1821A556B80212DEBEE69B096D` |
| Restoration provenance | User reported re-downloading the file on 2026-08-23; acquisition URL `UNKNOWN`; byte identity exactly matches the pre-existing lock |
| Evidence class | `PAPER-SPECIFIED` |

The arXiv record reports v1 on 2016-08-25, v2 on 2016-11-29, v3 on 2016-12-03, v4 on 2017-08-27, and v5 on 2018-01-28: <https://arxiv.org/abs/1608.06993>.

## Publication copy used only for version comparison

| Field | Verified value |
|---|---|
| Local file | `sources/papers/DenseNet_CVPR2017.pdf` |
| Official source | <https://openaccess.thecvf.com/content_cvpr_2017/papers/Huang_Densely_Connected_Convolutional_CVPR_2017_paper.pdf> |
| Venue | CVPR 2017, pp. 4700-4708 |
| Pages | 9 |
| SHA256 | `94D6252E5508EB047BE64BBC7BD095A46064D0B51FC73206D9591578477AAEE1` |
| Evidence class | `PAPER-SPECIFIED` for the publication copy; the user-supplied v5 remains the primary paper |

### Substantive CVPR-to-arXiv-v5 differences

- CIFAR Table 2, CIFAR architecture definitions, CIFAR preprocessing, and CIFAR training protocol are substantively unchanged.
- CVPR Table 1/3 contains DenseNet-161 (`k=48`); arXiv v5 replaces it with DenseNet-264 (`k=32`) and updates the ImageNet block counts and errors.
- The CVPR copy describes a batch-size/epoch exception for its largest ImageNet model; v5 removes that exception and adds the memory-efficient DenseNet technical-report note/citation.
- Reference numbering, acknowledgements, and typesetting changed. These do not change the CIFAR target evidence.

## Author official repository

| Field | Verified value |
|---|---|
| Repository | <https://github.com/liuzhuang13/DenseNet> |
| Local forensic clone | `sources/DenseNet-official` |
| Current remote HEAD observed during Phase 0 | `e3d24fb44997875f6eddc90dfd605e028d052bad` |
| Pinned official snapshot candidate | `6d4c8da6a1ef750c9116807b98e7c6265f51d762` |
| Commit date | 2017-08-23 16:04:52 -04:00 |
| Commit subject | `minor rearrange` |
| Local state | detached HEAD, clean |
| Evidence class | `OFFICIAL-CODE-SPECIFIED` |

Why this candidate: commit `4b5cc63ab40caa556c5a8b5d589f53bcb9c1e9b7` added the complete runner/data/checkpoint support on 2017-08-23; `6d4c8da...` is the last code adjustment that day. The relevant Lua files are byte-identical from this pin through the repository's current HEAD. This is an **official post-publication executable snapshot candidate**, not proof of the authors' private experiment commit.

Historical milestones kept distinct:

- `cbb6bff0b4bc8a0eba1f89f60b721e1a264d2afd` (2016-08-25): first public basic DenseNet model, contemporaneous with arXiv v1.
- `e6c89f2af885184b90272024246a53b155840b11` (2016-11-30): public DenseNet-BC model, contemporaneous with the v2/v3 revision period.
- `6d4c8da...` (2017-08-23): complete runnable snapshot selected for Phase 0 code semantics.

### Framework provenance - kept separate

| Framework path | Provenance judgment | Phase 0 use |
|---|---|---|
| Lua/Torch7 in `liuzhuang13/DenseNet` | Author-controlled and contemporaneous with the paper revisions; earliest model commit is 2016-08-25 and BC appears 2016-11-30. This is the primary paper-era implementation evidence. | **Primary official-code evidence** |
| Caffe links labeled "Our Caffe Implementation" in the official README | Author-endorsed/author-linked, but separate from the Lua/Torch training path and not shown to be the source of Table 2 runs. | Secondary cross-check only; not used to override Lua/Torch |
| PyTorch/torchvision links in the official README | PyTorch usage was added to README history in April 2017; memory-efficient PyTorch was linked later. No evidence shows that these ports produced the paper's CIFAR Table 2. | Not paper-era evidence; future PyTorch work is explicitly a modern-framework reproduction |
| Third-party TensorFlow/Keras/MXNet/Lasagne/Chainer ports | Listed as other implementations, not primary author experiment sources. | Excluded as primary evidence |

This separation prevents a later torchvision DenseNet behavior from being silently substituted for the CIFAR architecture in the paper.

## Historical dependency candidates

These repositories were not pinned by the DenseNet repository. They are date-aligned candidates selected as the latest commits not later than the official snapshot cutoff; each pin has status **`HISTORICAL-DEPENDENCY-CANDIDATE`** and is **not claimed to be the exact installed version used by the authors**. Claims directly supported by their source are classified `HISTORICAL-DEPENDENCY-BACKED`, with the candidate limitation kept visible.

| Dependency | Repository | Candidate commit | Commit date | Local path | Classification |
|---|---|---|---|---|---|
| fb.resnet.torch | <https://github.com/facebook/fb.resnet.torch> | `ef12212f88f4988d4b8f0c87fed133f463dc14a8` | 2017-02-09 | `sources/fb.resnet.torch` | `HISTORICAL-DEPENDENCY-CANDIDATE` |
| Torch optim | <https://github.com/torch/optim> | `656c42af1f996e4a5d6aae3b9aeac831ca162241` | 2017-02-08 | `sources/torch-optim` | `HISTORICAL-DEPENDENCY-CANDIDATE` |
| Torch nn | <https://github.com/torch/nn> | `bae729acce1930aa46be5c6ca0d7272f7eba406e` | 2017-08-03 | `sources/torch-nn` | `HISTORICAL-DEPENDENCY-CANDIDATE` |
| cudnn.torch | <https://github.com/soumith/cudnn.torch> | `008c49de3982119378576fa4244e472a50fd9ebe` | 2017-07-07 | `sources/cudnn.torch` | `HISTORICAL-DEPENDENCY-CANDIDATE` |

## Relevant-file SHA256 ledger

| File | SHA256 |
|---|---|
| `sources/DenseNet-official/models/densenet.lua` | `5C9177DC0E6293E004C87F093BD69FCB76F189959472E143FE6F026EE3651DBC` |
| `sources/DenseNet-official/models/DenseConnectLayer.lua` | `A9CB7EFC2AED4A1C0A3319E6E9FF8036B91E12DB263F69F3214D2FCDF96E0688` |
| `sources/DenseNet-official/train.lua` | `DBEE340F5759A16BCA97CEA3258EE815E69B522E47C4D78DB704288CF3C9F83F` |
| `sources/DenseNet-official/main.lua` | `62BE35DFAF63FE02ED33266F5AE6667F33E90A1CD709FB9A49BA4C601B34DAEF` |
| `sources/DenseNet-official/opts.lua` | `50F8DF279B70EE314220063481D188C421EFDD33B8ED81A0572C97E05696A693` |
| `sources/DenseNet-official/dataloader.lua` | `655436B96CB712C5EDECB1AE51DBA0ACF11FC91FDCFFA7DCF0DE354C71B74780` |
| `sources/DenseNet-official/datasets/cifar10.lua` | `77231391FF85890452B18368089658BC773CF463ADA69F4B7A9A413C9063F507` |
| `sources/DenseNet-official/datasets/cifar10-gen.lua` | `923658EB03D2D2D0CEE45CE2A5254DC0EB505E3BF1A35F7F4E18B6F8DAE8822F` |
| `sources/DenseNet-official/datasets/init.lua` | `7263F1705577908AE997980905994877A904146E996B319EE895F6684D11D4F0` |
| `sources/DenseNet-official/datasets/cifar100.lua` | `A725FD09F116549A4D81E12299DCD51BABFFD33136750414E36DC384E6D5C769` |
| `sources/DenseNet-official/datasets/transforms.lua` | `20692519D9029E7E4CB87C32AF7910D4A221CE4A2D313A7C3423E1943A0C6C27` |
| `sources/torch-optim/sgd.lua` | `B9A094B0545E2F081C475513A0F47ACDB8BDA227C1C310FDE5806A37E1276FF0` |
| `sources/torch-nn/Linear.lua` | `68F66F41B4FE3E3D3BADE747BE55977B800B4C18E9A5EF11697024EE5C17E431` |
| `sources/torch-nn/Dropout.lua` | `BB229EF355D167C2FA217AC45A91709B9706E1D6B7D85993D91907BF08AD44AF` |
| `sources/torch-nn/lib/THNN/generic/BatchNormalization.c` | `B97B33BA25117F03242B74104032185739A9B3838996CDBF7EA799894DEEE2AE` |
| `sources/cudnn.torch/BatchNormalization.lua` | `FABCE6271B5968A34E5920FE9748151C205A72343F641AC65F47620B30A992BF` |
| `sources/cudnn.torch/test/test.lua` | `586FB6B6BDB7F05F92A56337D01A34F1CD31584E3547F4A8AB06FDD9DC3ACB48` |
