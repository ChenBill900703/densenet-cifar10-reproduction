# Phase 4 Entry Decision Proposal v1

Status: **HUMAN-APPROVED 2026-08-23 / PHASE 4 CLOSED DIAGNOSTIC AUTHORITY / NO FORMAL TRAINING**

Date prepared: **2026-08-23**

## 1. Purpose and current authority

Phases 1-3 are complete. Phase 4 is the exact-device feasibility and bounded end-to-end preflight gate for the approved `DenseNet-BC-100-12 / CIFAR-10+ / FP32 / physical batch 64 / 300 epochs` target on the local RTX 3070 Ti.

The human approved the exact authorization in section 6 on 2026-08-23. The authority is limited to the closed diagnostic and conditional forward-only scope recorded here.

The requested Phase 4 authority remains non-formal. Passing Phase 4 would still require a separate human completion decision and would not create a Phase 5 freeze or formal-training authority.

## 2. Evidence and unresolved question

| Item | Evidence | Phase 4 interpretation |
|---|---|---|
| Approved physical batch | Paper p.5 and official command specify batch 64; A-008 was human-approved | Batch 64 cannot be reduced or emulated by accumulation |
| Precision/graph | A-003, A-008, A-011 and completed Phase 3 | FP32 only; AMP, TF32, compile, recomputation, alternate memory layers, and accumulation remain off |
| Historical memory anchor | Official README `:143-151` reports 5,452 MB at batch 64 on one Titan X without memory optimization | `OFFICIAL-CODE-SPECIFIED` historical anchor only; it cannot be transferred numerically to PyTorch/RTX 3070 Ti |
| Current GPU | RTX 3070 Ti, 8,192 MiB, UUID `GPU-9f68fb0f-9bd0-a95c-d16e-8362b9d59e2e`, compute capability 8.6 | Exact-device identity must be recaptured inside every fresh diagnostic worker |
| Display/WDDM pressure | Earlier inspection observed about 1,195 MiB already occupied | Available VRAM is external state and must be measured, never inferred from nominal capacity |
| Mechanics | Phase 3 accepted source `c890b2c7e94bdf50af54c075887379a2c5394643` | Exact SGD/loss/LR/RNG/checkpoint mechanics may be reused only within the authority below |
| Remaining question H-002 | Exact batch-64 PyTorch peak and replay behavior are unmeasured | Phase 4 must report observed capacity without silently changing the protocol |

Every measured memory/time/fit result will be `DERIVED`. The choice of measurement protocol below is an `IMPLEMENTATION-ASSUMPTION`. No Phase 4 observation is a `FORMAL-REPRODUCTION-RESULT`.

## 3. Proposed decisions

### A-013 - Exact batch-64 synthetic capacity trajectory

Approve one generated-data-only Phase 4 diagnostic with the following closed protocol:

1. A parent process creates two fresh GPU workers with `CUBLAS_WORKSPACE_CONFIG=:4096:8` set before Python starts.
2. Both workers require the exact approved GPU identity and enforce deterministic algorithms, cuDNN benchmark off/deterministic on, convolution and matmul FP32 policy `ieee`, FP32 parameters/inputs, and no AMP/compile/recomputation/alternate memory path.
3. Worker A constructs the approved model and single-group optimizer, initializes the approved runtime RNG domains, and uses physical generated batches of exactly 64 without accumulation.
4. Worker A executes one generated warm-up optimizer call to materialize gradients and all 299 momentum buffers, resets CUDA peak counters, then executes ten measured generated optimizer calls. It saves one synthetic checkpoint after total call 6 and finishes at total call 11.
5. Worker B starts fresh, verifies and loads Worker A's call-6 checkpoint, then replays calls 7-11 from the same explicit generated batches.
6. Worker A and Worker B must finish with bit-exact loss suffixes, full model/BatchNorm state, optimizer state, and step ledger.

This protocol executes exactly **16 non-formal synthetic optimizer calls**: 11 in Worker A and five in Worker B. It reads no CIFAR data and leaves formal optimizer steps at zero.

The generated batch seeds are Phase 4 diagnostic coordinates, not project training seeds and not paper seeds. They will be derived by the same approved SHA256 framing from the dedicated test-only domain `densenet-phase4-synthetic-batch-v1|MASTER_SEED|CALL_INDEX`, using only the first preregistered project master seed. The other two project seeds do not need duplicate capacity runs because device memory shape is seed-invariant; their runtime-domain derivations were already validated in Phase 3.

### M-005 - Memory and timing measurement definitions

Approve recording, without an automatic safety-margin threshold:

- GPU name, UUID, compute capability, total memory, driver, WDDM mode where available, Python/PyTorch/CUDA/cuDNN versions, environment-lock SHA256, source commit, and every deterministic/precision flag;
- `torch.cuda.mem_get_info()` free/total bytes before model construction, immediately before the measured interval, and after synchronization;
- PyTorch allocated/reserved bytes after model, generated batch, forward, backward, first optimizer update, every measured update, and checkpoint reload;
- peak allocated and peak reserved bytes after resetting counters following the first update;
- all ten synchronized measured-update durations, plus their arithmetic mean, median, minimum, and maximum;
- optimizer-state tensor count, gradient count, BN counter state, checkpoint SHA256, final state hashes, and all prohibited-scope counters.

The package deliberately does not invent a universal VRAM-headroom cutoff. Phase 4 technical output uses only these dispositions:

- `OBSERVED-FIT`: the exact closed diagnostic completes without OOM/non-finite state and replay is exact;
- `OBSERVED-NOT-FIT`: the exact protocol raises CUDA OOM;
- `INVALID`: identity/policy/hash/state/replay checks fail.

Measured free headroom and WDDM/display conditions must be shown to the human in the Phase 4 completion package. Only that later human decision may accept or reject practical feasibility. A timing projection may multiply the measured synthetic-update mean by 234,600 paper-derived updates, but it must be labeled a generated-kernel projection excluding real DataLoader, evaluation, checkpoint, and system-contention overhead.

### A-014 - One bounded CIFAR forward-only integration preflight

Approve exactly one real-data integration preflight after the synthetic capacity/replay result is `OBSERVED-FIT`:

1. Reverify the sole approved Toronto binary archive SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD` before decoding.
2. Use project master seed `1021082110`, candidate epoch 1, and the already-approved permutation/augmentation mapping.
3. Restrict the sampler to the first 64 explicit epoch decisions so workers cannot prefetch or decode any sample outside the bounded set.
4. Use physical batch 64, `num_workers=2`, `drop_last=false`, `pin_memory=false`, and a blocking CPU-to-GPU copy. These transfer choices are diagnostic mechanics, not a Phase 5 freeze.
5. Construct a fresh approved model, apply the approved deterministic/runtime RNG policy, enter train mode, and perform exactly one forward call.
6. Verify input shape/dtype, raw-logit shape `[64,10]`, finiteness, all 99 BatchNorm counters advancing once, and record exact input/logit/state hashes.

This is a narrowly authorized raw-logit integration check. It must not compute cross-entropy, backward, gradients, optimizer state/update, class indices/argmax, prediction files, accuracy, error rate, ranking, or checkpoint selection. Exactly 64 CIFAR training samples may be decoded and consumed; CIFAR optimizer steps remain zero.

If the synthetic result is not `OBSERVED-FIT`, the CIFAR forward-only preflight must not run.

### H-008 - Fail-closed feasibility disposition

Approve the following rule:

- OOM, insufficient headroom concerns, external GPU contention, driver reset, non-finite state, identity mismatch, or replay mismatch cannot authorize a workaround.
- Do not reduce batch size/resolution, enable AMP/TF32/compile/recomputation, use accumulation, change the model, or close other user applications automatically.
- Preserve the failure report, keep Phase 4 incomplete, and request a new human decision.
- An `OBSERVED-FIT` result is not automatically Phase 4 completion; it proceeds to a separate completion decision package with all memory/timing/environment evidence.

## 4. Mandatory Phase 4 acceptance tests

1. Fail closed unless the GPU UUID/name/capability, FP32 model/input, deterministic settings, IEEE precision policies, environment lock, source commit, and approved target all match.
2. Prove physical generated batch 64 with no microbatching or accumulation.
3. Materialize and validate all 299 gradients and momentum buffers under the single approved optimizer group.
4. Record stage-level and per-step allocated/reserved/free/peak memory in bytes and synchronized latency for the closed 1+10 trajectory.
5. Require finite losses, gradients, parameters, BN buffers, momentum buffers, and every memory/timing value.
6. Require Worker A versus fresh Worker B bit-exact suffix losses, complete model/BN state, optimizer state, checkpoint identity, RNG restoration, and synthetic ledger.
7. Test fail-closed behavior for a forged batch size, AMP/autocast, TF32, compile wrapper, wrong GPU/environment/source/config hash, missing memory field, non-finite value, and checkpoint/replay mismatch.
8. Only after `OBSERVED-FIT`, consume exactly the bounded 64 CIFAR records and prove one train-mode raw-logit forward with no loss/backward/optimizer/prediction/accuracy path.
9. Store a machine-readable report that distinguishes 16 synthetic optimizer calls, zero CIFAR optimizer calls, zero formal optimizer steps, 64 bounded CIFAR samples, one raw-logit forward, and zero loss/backward/argmax/accuracy/pretrained operations on CIFAR.
10. Rerun the full regression suite, source verifier, `pip check`, compilation, and the current-source fresh external environment checks.

Passing these obligations would technically validate Phase 4 only. A separate human completion decision would still be required before Phase 5 planning.

## 5. Authority if approved

Approval permits only:

- implementation/tests for the closed Phase 4 diagnostic;
- exactly 16 generated-data non-formal optimizer calls in its dated machine diagnostic;
- exact-device memory/timing capture;
- conditional decoding of 64 approved CIFAR training samples and one train-mode raw-logit forward with no loss/backward/optimizer/prediction/accuracy.

Approval continues to prohibit:

- every CIFAR optimizer step and CIFAR training loop/partial epoch;
- CIFAR loss, backward, gradients, optimizer state/update, prediction/argmax, accuracy/error, validation/test execution, or result selection;
- pretrained weights/results;
- any protocol workaround after OOM;
- Phase 5 freeze or formal optimizer step.

Formal optimizer steps remain **0**.

## 6. Exact proposed authorization

**「我批准 Phase 4 entry decision package v1：批准 A-013 的 exact-device batch-64 FP32 合成容量與 fresh-process checkpoint replay protocol，固定 Worker A 11 次、Worker B 5 次，共 16 次 non-formal synthetic optimizer calls；批准 M-005 的逐階段 allocated/reserved/free/peak VRAM bytes、10 次同步 update timing 與無自動 headroom threshold 的 `OBSERVED-FIT`／`OBSERVED-NOT-FIT`／`INVALID` 報告規則；批准 A-014 僅在 synthetic `OBSERVED-FIT` 後，使用 project seed 1021082110、epoch 1、workers=2，限制解碼前 64 筆 approved CIFAR training samples，執行一次 train-mode raw-logit forward-only integration preflight；批准 H-008 fail-closed feasibility disposition；開始 Phase 4。仍禁止 CIFAR loss、backward、optimizer step、training、prediction/argmax、accuracy/error、validation/test execution、pretrained results、任何 OOM 後 protocol workaround、Phase 5 freeze 與正式 optimizer step；formal optimizer steps 維持 0。」**

## 7. Status before human decision

`PHASE 4 ACTIVE - CLOSED DIAGNOSTIC SCOPE ONLY`
