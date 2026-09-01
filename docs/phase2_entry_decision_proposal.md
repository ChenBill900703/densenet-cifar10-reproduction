# Phase 2 Entry Decision Proposal v1

Status date: **2026-08-16**

Status: **HUMAN-APPROVED 2026-08-16 / PHASE 2 AUTHORITY / NOT PHASE 5 FROZEN**

This document was first committed as an unapproved preregistered recommendation before any dataset access, optimizer construction, accuracy evaluation, or formal result. The human then approved it verbatim on 2026-08-16. That approval authorizes CIFAR artifact, transform, and DataLoader validation in Phase 2. It does not authorize optimizer construction, training, accuracy evaluation, pretrained-result download, or a formal optimizer step.

## Recommended decision package

| Gate | Recommended project decision | Evidence class and consequence |
|---|---|---|
| A-001 | Use modern PyTorch while matching the pinned paper/Torch7 mathematics rather than Torch7 object layout. | `IMPLEMENTATION-ASSUMPTION`; formalizes the already validated porting approach. |
| B-002 / A-004 / C-001 | For every formal seed, train all 300 epochs without evaluating the test set. Evaluate the epoch-300 checkpoint exactly once. Never select or report a best-test epoch. | Paper-faithful `IMPLEMENTATION-ASSUMPTION`; intentionally rejects the conflicting post-publication runner behavior. |
| B-003 / A-002 | Use exactly three independent `PROJECT REPRODUCTION SEEDS`: `1021082110`, `1747066946`, and `869460408`. Report all three final test errors; use their arithmetic mean as the primary project reproduction result and sample standard deviation as a variability descriptor. Never select the best seed. | `IMPLEMENTATION-ASSUMPTION`; the paper does not disclose seeds, run count, or aggregation. The transparent derivation below prevents result-driven seed selection. |
| B-004 / A-003 / C-006 | Use deterministic PyTorch/CUDA algorithms; set `CUBLAS_WORKSPACE_CONFIG=:4096:8` before Python starts; enable `torch.use_deterministic_algorithms(True)`; set cuDNN benchmark off and deterministic mode on; set convolution and matmul FP32 precision policy to IEEE; disable TF32, AMP, and compilation. | `IMPLEMENTATION-ASSUMPTION`; prioritizes audit replay over the official runner's nondeterministic `fastest` default. Phase 1 diagnostics directly show that the choice changes gradients. |
| B-005 / A-005 | Adopt BatchNorm with `eps=1e-5`, affine enabled, coefficient `0.1`, gamma/beta `1/0`, running mean/variance `0/1`, biased (`/n`) training variance, and unbiased (`/(n-1)`) running-variance observation. Retain PyTorch's `num_batches_tracked` only as recorded state; fixed momentum must not depend on it. | `HISTORICAL-DEPENDENCY-BACKED` semantics plus an explicitly approved port assumption. Accept semantic identity, not bitwise identity with the authors' unknown native cuDNN build. |
| B-006 / A-006 / C-005 | For classifier fan-in 342, initialize weights uniformly in `[-1/sqrt(342), +1/sqrt(342)]` and set classifier bias to exactly zero. | `HISTORICAL-DEPENDENCY-BACKED` candidate adopted as an `IMPLEMENTATION-ASSUMPTION`; the exact author-installed Torch nn commit remains unknown. |
| A-008 | Preserve physical batch size 64 in FP32 with no gradient accumulation. If exact-device Phase 4 feasibility fails, stop and request a new human decision rather than silently changing the protocol. | `IMPLEMENTATION-ASSUMPTION`; preserves the approved target and governance constraint. |

## Seed preregistration derivation

The seed values were derived before any dataset access, optimizer construction, accuracy evaluation, or formal result existed.

1. UTF-8 source string:
   `DenseNet-BC-100-12|CIFAR-10+|PROJECT-REPRODUCTION-SEEDS|2026-08-16|v1`
2. SHA256:
   `3CDC79FE6822204233D2E9B8F38B764409099FD31666E887DB444101336620ED`
3. Split the first 12 digest bytes into three consecutive unsigned 32-bit big-endian integers.
4. Apply bit mask `0x7FFFFFFF` to each integer.
5. Preserve the resulting order: `1021082110`, `1747066946`, `869460408`.

These are project provenance seeds, never paper seeds. Phase 3 must define and test how each master seed maps to Python, PyTorch CPU/CUDA, sampler, augmentation, and worker RNG streams; approving this list does not silently resolve H-003.

## BatchNorm acceptance oracle

Approval of B-005 would freeze the semantic rule, not an unsupported cross-framework bitwise claim. Its acceptance tests are:

- the float64 analytic two-batch oracle uses `rtol=1e-12`, `atol=1e-12` for train output, running mean, running variance, and eval output;
- the same-backend functional full-graph oracles require `rtol=0`, `atol=0` for outputs and state, and exact input/all-parameter gradient agreement;
- all 99 BatchNorm modules must have the approved constants and initial state;
- checkpoint round-trip must preserve every parameter, running buffer, counter, state hash, and eval logits exactly;
- no claim is made that modern PyTorch reproduces the authors' unknown cuDNN binary reduction order bit-for-bit.

## Reporting rule

The formal report would show, without selection:

1. the paper reference error, **4.51%**, explicitly labelled as the paper value;
2. each of the three epoch-300, one-time-test project errors;
3. the arithmetic mean of those three errors as the primary reproduction result;
4. the sample standard deviation as a variability descriptor;
5. the signed difference between the project mean and the paper reference.

No best seed, best checkpoint, test-guided retry, post-hoc seed replacement, or test-set-based configuration change is permitted.

## Items deliberately not resolved by this package

- A-007/H-001/M-001: exact CIFAR archive choice and SHA256;
- H-003: worker count and master-seed-to-worker/augmentation RNG mapping;
- H-004: tested PyTorch realization of the epoch-150 and epoch-225 LR boundaries;
- H-002: batch-64 peak-memory feasibility with the eventual optimizer state;
- H-005: any memory-saving path equivalence;
- H-006: trajectory-preserving checkpoint/resume design;
- evaluation batch size/worker count, environment artifact hashes, and the Phase 5 configuration hash.

Those are later validation/freeze obligations. No optimizer or formal training is authorized by a Phase 2 entry decision.

## Exact proposed authorization

For an unambiguous audit trail, the human approved this proposal by stating exactly:

**「我批准 Phase 2 entry decision package v1，包含 A-001、A-002、A-003、A-004、A-005、A-006、A-008，以及 B-002 至 B-006 的建議處置；開始 Phase 2，但仍禁止 optimizer 與正式訓練。」**

The approval applies only to the explicitly named decisions and restrictions. It does not approve A-007, any unresolved HIGH/MEDIUM item, Phase 3, Phase 5 freeze, or formal training.
