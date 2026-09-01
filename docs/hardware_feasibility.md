# RTX 3070 Ti Pre-Phase-4 Feasibility Record

The earlier sections preserve planning estimates and are not permission to train. The approved closed Phase 4 measurement produced `OBSERVED-FIT`, and the human accepted it within the recorded scope on 2026-08-23.

## Verified local hardware snapshot

Observed 2026-08-16 with `nvidia-smi`:

| Field | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 3070 Ti |
| Total VRAM | 8192 MiB |
| Driver | 591.86 |
| Reported CUDA compatibility | 13.1 |
| Driver model | WDDM, display attached |
| VRAM occupied at inspection | about 1195 MiB |

Only roughly 7 GiB was free in the observed desktop state. Phase 4 must measure the actual fresh-process headroom and cannot rely on nominal 8 GB.

## Evidence anchors

- The official README reports DenseNet-40-12 on one Titan X, cuDNN v5, batch 64, 300 epochs taking about 6 hours (historical README commit `e385717...`).
- The official README reports DenseNet-BC-100-12 at batch 64 without memory optimization using 5,452 MB and 0.156 s/iteration on one Titan X (`README.md:143-151`). At 782 updates/epoch and 300 epochs, the raw training-loop anchor is about 10.2 hours, excluding full evaluation/checkpoint overhead.
- The official README reports BC-190-40 requiring 8.3 GB even with `optMemory=4` on a 12 GB Titan X (`README.md:85-88`). This is unsafe on a display-attached 8 GB card.

These Torch/Titan X numbers are not directly transferable to modern PyTorch/RTX 3070 Ti. They are evidence anchors for ordering and feasibility only.

## Candidate assessment

Time ranges are conservative Phase 0 estimates for one 300-epoch seed, including expected evaluation/checkpoint overhead but excluding setup/debug time. They must be replaced by Phase 4 measurements without executing a formal CIFAR optimizer step.

| Candidate | Params | Batch 64 FP32 on 8 GB | Estimated time/seed | One-week judgment | Evidence quality |
|---|---:|---|---|---|---|
| DenseNet-40-12 | 1.0M | Likely feasible | 4-10 h | Strong | Medium: official 6 h Titan X anchor; late runner initial-channel conflict must be avoided |
| DenseNet-100-12 | 7.0M | Likely feasible with a careful implementation; activation-heavy | 10-24 h | Strong for one/few seeds | Low-medium: no direct memory/time row |
| DenseNet-100-24 | 27.2M | Borderline; must not assume fit | 24-60 h | Weak until preflight | Low |
| DenseNet-BC-100-12 | 0.8M | **Likely feasible**; official 5.452 GB no-optimization anchor | 6-16 h | **Strongest** | Medium-high |
| DenseNet-BC-250-24 | 15.3M | Borderline; memory-efficient implementation probably required and must prove semantic equivalence | 24-60 h | Possible for one seed, poor for multiple seeds | Low |
| DenseNet-BC-190-40 | 25.6M | **Not protocol-safe on this machine based on current evidence**; official memory anchor exceeds practical free VRAM | 30-72 h if it fit | Reject as primary | Medium for rejection |

Dataset choice (C10 vs C100) changes only classifier size and has negligible compute/memory effect. Augmentation adds input-pipeline work; no-augmentation dropout adds modest model work.

## Approved-target feasibility disposition

`DenseNet-BC-100-12 / CIFAR-10+` is the approved primary target. Phase 4 has now established exact-device `OBSERVED-FIT` for the closed diagnostic, while the formal multi-seed runtime remains a projection rather than a completed-run observation. A same-architecture CIFAR-100+ run is merely a possible later target and is not approved in this lifecycle. The approved three formal seeds may exceed one week; the recorded timing evidence must remain visible without silently reducing the preregistered count.

## Phase 4 acceptance conditions

The exact closed protocol, measurement definitions, synthetic-call count, conditional 64-sample CIFAR forward-only exception, and fail-closed dispositions are approved in `phase4_entry_decision_proposal.md`; no expansion or workaround is authorized.

Observed on 2026-08-23 at source `f91cdf6`: peak allocated 2,336,236,544 bytes, peak reserved 2,680,160,256 bytes, minimum observed free 4,652,531,712 bytes, and ten-update mean 0.3053955800016411 seconds. Exact scope and caveats are in `phase4_validation_2026-08-23.md`.

On the exact GPU, with batch 64 and FP32:

- AMP off, TF32 off, compile off, no gradient accumulation.
- Deterministic policy exactly matches the approved assumption.
- After the Phase 3 mechanics gate authorizes it, model, loss, non-formal optimizer state, input batch, gradients, and CUDA RNG all reside as intended.
- A **non-formal synthetic** forward/backward/optimizer update fits with adequate safety margin; it must not use CIFAR and must never be counted as a formal optimizer step.
- Fresh-process replay matches exactly under the chosen deterministic policy.
- Checkpoint restore preserves model, optimizer momentum, BN buffers, all RNG states, epoch/update cursor, and data order.
- CIFAR forward-only preflight may occur only when authorized by the phase plan; CIFAR optimizer-step count must remain 0 before formal authorization.

If batch 64 does not fit, report infeasibility. Do not enable AMP, accumulation, smaller batches, or reduced resolution as a hidden workaround.
