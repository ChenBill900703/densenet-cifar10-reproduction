# Phase 4 Exact-Device Technical Validation - 2026-08-23

Status: **TECHNICALLY VALIDATED / OBSERVED-FIT / HUMAN-ACCEPTED 2026-08-23**

This record is exact-device feasibility evidence, not a formal reproduction
result and not permission to enter Phase 5 or train on CIFAR.

## 1. Locked execution identity

| Item | Exact identity |
|---|---|
| Phase 4 authorization commit | `0658843ec9797cfb0940c6c275ef897fc5d67b1d` |
| Diagnostic source commit | `f91cdf6ee5e8fafd20148af3313b3a56a16e6747` |
| Machine report | `evidence/phase4_exact_device_2026-08-23.json` |
| Machine report SHA256 | `7B22E8B5E97F7BFED961C1CC12F9F4E8A6BF56D9680A147CBC83910E66FAE906` |
| Phase 4 config SHA256 | `8BE9E997ABC2ED18F151DEE304F20374E8E6266158559A412CA07C9ADD7567FA` |
| Environment-lock SHA256 | `C65D2C940A4A26C9C86BBB05859DD2405C3C351672720AB0E71D9572944722FC` |
| Approved CIFAR binary SHA256 | `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD` |

The root worktree was clean before the diagnostic. The report identifies
PyTorch `2.12.1+cu130`, CUDA `13.0`, cuDNN `92000`, driver `591.86`, WDDM,
the exact approved RTX 3070 Ti UUID, and compute capability 8.6. Deterministic
algorithms were on; cuDNN benchmark was off/deterministic on; convolution and
matmul policies were IEEE FP32; AMP, compile, recomputation, and accumulation
were absent.

## 2. A-013 synthetic capacity and replay

The closed diagnostic executed exactly:

- Worker A: one warm-up plus ten measured physical-batch-64 generated updates,
  11 optimizer calls total;
- checkpoint after total call 6;
- fresh Worker B: replay of calls 7-11, five optimizer calls;
- combined Phase 4 count: 16 non-formal synthetic optimizer calls;
- all 299 gradients and all 299 momentum buffers present and finite;
- all 99 BatchNorm counters reached 11 on Worker A.

Worker A and fresh Worker B were bit-exact for suffix losses, complete
model/BatchNorm state, optimizer state, checkpoint identity, checkpoint RNG
state, and final step ledger. The final Worker-A state identities were:

- model: `23EF725FBFADF3376CB8222397BB47F0C1AFDB376A5E9C127F39A4066363ED0C`;
- optimizer: `6E0964ECA0499151EF2BB822FE43269D67E931C97C13E2ADA6A820BE765AE529`;
- checkpoint artifact: `85D68BE96925D87B2196B97C97044A18383836436C5DDCA8A68042E4EE8A87D0`.

Disposition: **`OBSERVED-FIT`**.

## 3. M-005 exact memory and timing evidence

The report contains 66 stage/per-update memory records in integer bytes.
Independent recomputation gives:

| Measurement | Bytes | MiB |
|---|---:|---:|
| Initial fresh Worker-A free memory | 7,435,452,416 | 7,091 |
| Maximum peak allocated | 2,336,236,544 | 2,228.0087890625 |
| Maximum peak reserved | 2,680,160,256 | 2,556 |
| Minimum observed free memory | 4,652,531,712 | 4,437 |

The ten synchronized update durations were all finite and positive. Their
arithmetic mean was `0.3053955800016411 s`, median
`0.30187904997728765 s`, minimum `0.2913320999359712 s`, and maximum
`0.3437653000000864 s`.

Multiplying the measured mean by the paper-derived 234,600 updates gives
71,645.803068385 seconds, or about 19.9016 hours. This is explicitly a
generated-kernel projection. It includes the required per-stage memory
instrumentation and excludes real DataLoader, evaluation, checkpoint, desktop
contention, and multi-run overhead; it is not a promised formal runtime.

No automatic headroom threshold was applied. The exact observations are
presented for the separate human completion decision.

## 4. A-014 bounded CIFAR integration

Because the synthetic result was `OBSERVED-FIT`, the conditional forward-only
worker ran once. It:

- reverified the sole approved 170,052,171-byte archive and SHA256;
- used project seed 1021082110, epoch 1, workers 2, physical batch 64;
- restricted the DataLoader sampler to exactly the first 64 full-epoch
  permutation/augmentation decisions;
- decoded exactly 64 training records and emitted one batch;
- used a blocking transfer, no pinning, and a fresh train-mode model;
- performed one `torch.no_grad()` raw-logit forward;
- produced finite FP32 logits of shape `[64,10]`;
- advanced all 99 BatchNorm counters exactly once;
- left every parameter gradient absent.

Exact hashes:

- request decisions: `A260DC9AB4F58EA4659F52BC207EBA173C12B6DBED9C7F4DD5A4D0F1A2D3337F`;
- transformed inputs: `D95F90DFEF92BE96A2603CF8F1E6EFDE4DE80F76A2C4A6BC0B46308A68CBEC32`;
- targets: `C751082AA3D3C66949EEEDD97F2CBCB8F8FEF2BA9B6D05A5E2DEE455CFEE01FA`;
- raw logits: `E9583F52AD23FBF271ACD7A5D5DBA633867FAA9E9B2D778C0FA1DF7360F68C90`.

CIFAR loss, backward, optimizer calls, prediction/argmax, accuracy/error, and
validation/test samples were all exactly zero.

## 5. Regression and reconstruction verification

- Project venv: **135/135 passed** under `-X dev -W error` in 85.72 seconds.
- Fresh project-external venv reconstructed from the README lock sequence:
  isolated editable import and `pip check` passed; **135/135 passed** under
  `-X dev -W error` in 84.54 seconds.
- Source verifier: 19/19 evidence files and 5/5 repositories passed.
- Compilation, `pip check`, and `git diff --check` passed.
- The temporary external environment was removed after verification.

The regression suite does not rerun the 16-call Phase 4 machine diagnostic. It
validates the stored report, recomputes its SHA/provenance/memory/timing/scope,
and tests fail-closed mutations. This preserves the exact authorized diagnostic
count.

## 6. Scope ledger and remaining authority

| Counter | Value |
|---|---:|
| Phase 4 non-formal synthetic optimizer calls | 16 |
| CIFAR samples read by Phase 4 model preflight | 64 |
| CIFAR raw-logit forward calls | 1 |
| CIFAR loss/backward/optimizer calls | 0 / 0 / 0 |
| Predictions/argmax and accuracy/error computations | 0 / 0 |
| Validation/test samples | 0 |
| Pretrained downloads | 0 |
| Formal optimizer steps | **0** |

The human accepted the separate completion package on 2026-08-23, completing
Phase 4 within this measured scope. Phase 5, CIFAR training, and every formal
optimizer step remain forbidden.
