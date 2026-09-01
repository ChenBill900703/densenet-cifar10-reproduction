# Phase 2 CIFAR-10 Artifact and Data-Pipeline Specification

Status date: **2026-08-23**

Status: **PHASE 2 COMPLETED / HOLD BEFORE PHASE 3 / NOT PHASE 5 FROZEN**

Authority: human approval D-008, committed before any dataset access as commit `c0b5331`, and completion approval D-010. Phase 2 inspected CIFAR artifacts and implemented/tested decoding, transforms, samplers, DataLoader behavior, and RNG replay. D-010 explicitly does not authorize Phase 3, an optimizer or scheduler, training, accuracy, pretrained results, or a formal optimizer step.

## 1. Artifact evidence

| Artifact | Provenance | Published identity | Current Phase 2 state |
|---|---|---|---|
| Toronto CIFAR-10 Python archive | Dataset authors' official page, `https://cave.cs.toronto.edu/kriz/cifar-10-python.tar.gz` | 163 MB; MD5 `c58f30108f718f92721af3b95e74349a` | 170,498,071 bytes; official MD5 matched; SHA256 `6D958BE074577803D12ECDEFD02955F39262C83C16FE9348329D7FE0B5C001CE`; full semantic verification passed |
| Toronto CIFAR-10 binary archive | Dataset authors' official page, `https://cave.cs.toronto.edu/kriz/cifar-10-binary.tar.gz` | 162 MB; MD5 `c32a1d4ab5d03f1284b67883e8d87530` | 170,052,171 bytes; official MD5 matched; SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD`; full semantic verification passed |
| Historical Torch7 conversion archive | DenseNet official `datasets/cifar10-gen.lua`: `http://torch7.s3-website-us-east-1.amazonaws.com/data/cifar-10-torch.tar.gz` | No digest published in the pinned source | The historical endpoint returned HTTP 403 on 2026-08-16. Bytes and exact equivalence remain `UNKNOWN`; no third-party replacement is accepted as official evidence. |

The Toronto page states 50,000 training and 10,000 test images, each 32x32 RGB, with five 10,000-record training batches and one 10,000-record test batch. It specifies both Python and binary layouts as one label followed by 3,072 channel-major, row-major uint8 pixels.

The committed Phase 2 diagnostic compared all 60,000 labels and all 184,320,000 pixel bytes. Python and binary canonical records are byte-exact, with train digest `A0181DA372C0D63A5920FDBEA2EC3F83ECBC552D378218E1CB473CF634941A3B` and test digest `8E2EB146AE340B09E24670F29CABC6326DBA54DA8789DAB6768ACF480273F65B`. Both have the same ten ordered class names; the binary text metadata alone contains one terminal blank line absent from the Python pickle metadata. This is recorded as a formatting difference, not hidden as byte identity. D-010 selects the binary archive as the sole formal dataset artifact and retains the Python archive only as equivalence evidence.

Data archives and derived caches live below ignored `data/`; their identities and derived content digests belong in committed evidence JSON, not in Git as 160+ MB binaries.

## 2. Decode contract

- Binary record: exactly 3,073 bytes, consisting of a label byte followed by 3,072 pixel bytes.
- Pixel tensor: `torch.uint8`, shape `[3,32,32]`, channel order RGB, with each channel stored row-major.
- Training set: `data_batch_1.bin` through `data_batch_5.bin`, concatenated in numeric order, exactly 50,000 records.
- Test set: `test_batch.bin`, exactly 10,000 records.
- Toronto labels are 0-9. The Torch7 loader adds one because `nn.CrossEntropyCriterion` is one-indexed; the PyTorch port retains 0-9 because PyTorch cross entropy is zero-indexed. This is a framework-index translation, not a class remapping.
- Every required extracted batch must be a regular non-symlink file of exactly 30,730,000 bytes. Hash mismatch, duplicate/missing member, symlink member, short read, invalid label, or wrong shape fails closed.

## 3. Transform contract

`OFFICIAL-CODE-SPECIFIED` from `datasets/cifar10.lua` and `datasets/transforms.lua`:

1. Convert uint8 values directly to FP32 while preserving the raw 0-255 scale.
2. Normalize each channel using the rounded constants:
   - mean `[125.3, 123.0, 113.9]`;
   - standard deviation `[63.0, 62.1, 66.7]`.
3. For training, draw a horizontal flip with probability 0.5 and apply it next.
4. Create a zero-valued FP32 border of four pixels on every side after normalization.
5. Draw integer crop offsets `x,y` independently from 0 through 8 inclusive and return a 32x32 crop.
6. For test data, perform normalization only.

Zero padding after normalization is materially different from padding a raw black image before normalization. Tests must explicitly distinguish those cases and must distinguish x/width from y/height.

## 4. Approved deterministic epoch mapping (not Phase 5 frozen)

The pinned Torch7 loader draws one main-process `randperm`, then executes augmentation RNG inside two scheduling-sensitive worker threads. Even with worker seeds, the exact assignment of samples/jobs to historical threads is not recoverable from the paper and can change the trajectory.

Phase 2 implemented and validated the following auditable mapping before D-010 approved it:

- derive separate permutation and augmentation stream seeds as the first 64 SHA256 bits, masked to 63 bits, from `densenet-cifar10-loader-v1|MASTER_SEED|EPOCH|STREAM`;
- create one exact `torch.randperm` from the permutation stream;
- in permutation order, draw flip, crop-x, and crop-y from the augmentation stream;
- send the explicit sample index and three explicit choices to workers;
- never draw augmentation randomness inside a worker.

This makes outputs independent of worker count and scheduling. It is a trajectory-changing, human-approved `IMPLEMENTATION-ASSUMPTION`. D-010 fixes training `num_workers=2`; the mapping still requires later enforcement validation and Phase 5 freeze.

## 5. Phase 2 test obligations

1. Verify official MD5 plus locally recorded SHA256 and exact byte length for both Toronto archives. **Passed.**
2. Compare all 60,000 labels and all 184,320,000 pixel bytes across Python and binary archives. **Passed.**
3. Verify train/test counts and per-class histograms: 5,000/class train and 1,000/class test. **Passed.**
4. Safely materialize only the six required binary batch files and hash each derived file. **Passed.**
5. Verify CHW decode, row-major order, zero-based targets, and failure on invalid artifacts/records. **Passed.**
6. Independently test raw-scale normalization and exact transform order, including offset 8. **Passed.**
7. Verify sampler replay, epoch/seed separation, full permutations, and decision bounds. **Passed before approval; mapping approved by D-010.**
8. Require byte-exact batch/target replay between zero and two workers for the candidate mapping. **Passed on synthetic and full data.**
9. Run a complete 50,000-sample candidate epoch through both worker settings and compare ordered tensor/target hashes without model execution or accuracy. **Passed.**
10. Record every command, environment, hash, limitation, and optimizer step count (which must remain zero). **Passed; optimizer steps remain zero.**

## 6. Gate

All technical obligations above pass, D-010 approves A-007/H-001/M-001, H-003, M-002, and M-003, and Phase 2 is complete. At that milestone the project was held before Phase 3; later D-012 separately authorized generated-only Phase 3 mechanics. Neither decision authorizes CIFAR training, accuracy, or a formal run.
