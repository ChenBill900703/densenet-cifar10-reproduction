# Phase 3 Technical Validation - 2026-08-23

## Disposition

Phase 3 technical obligations passed. This is `DERIVED` mechanics evidence on generated tensors, not a formal reproduction result. A separate human completion decision is required before Phase 3 can be marked complete. Phase 4, CIFAR optimizer steps/training, prediction, accuracy, pretrained results, Phase 5 freeze, and formal optimizer steps remain forbidden.

## Audited source and scope

- Approval-only commit before optimizer implementation: `5ca9b7261b9cc90faa188bd0460adfb0ab558b6b`.
- Mechanics implementation lineage used by the dated GPU report: `c890b2c7e94bdf50af54c075887379a2c5394643`.
- Approved dataset SHA256 was recorded only as checkpoint provenance; no CIFAR sample was opened or passed through the model/optimizer by the Phase 3 diagnostic.
- Machine-report optimizer calls: five `NON-FORMAL-SYNTHETIC-OPTIMIZER-MECHANICS` calls, representing a three-step uninterrupted path and a two-step resumed suffix.
- Formal optimizer steps: **0**.

Pytest creates additional isolated generated-only mechanics calls while exercising rejection and round-trip cases. Those invocations are not a persistent run and are not combined into a training trajectory. The committed machine report is the exact bounded step ledger for the professor-facing replay diagnostic.

## Acceptance results

| Obligation | Result | Evidence class |
|---|---|---|
| Historical first/subsequent SGD equation, coupled decay, momentum, Nesterov | Passed against an independent scalar/vector oracle | `HISTORICAL-DEPENDENCY-BACKED` + `DERIVED` |
| One parameter group, all 299 trainable tensors once, BN affine and classifier bias decayed | Passed | `OFFICIAL-CODE-SPECIFIED` + `DERIVED` |
| Raw-logit unweighted mean cross-entropy value/gradient | Passed independent FP32 oracle with explicit last-bit tolerance | `HISTORICAL-DEPENDENCY-BACKED` + `DERIVED` |
| LR epochs 1/149/150/224/225/300 and fail-closed 0/301 | Passed | `OFFICIAL-CODE-SPECIFIED` + `DERIVED` |
| Full-model generated step, all gradients/model/optimizer state finite | Passed | `DERIVED` |
| All three project master seeds and model/Python/CPU/CUDA/worker domains | Replay and separation passed | `IMPLEMENTATION-ASSUMPTION` + `DERIVED` |
| Strict checkpoint round-trip and fail-closed mutation corpus | Passed | `IMPLEMENTATION-ASSUMPTION` + `DERIVED` |
| Deterministic GPU uninterrupted versus resumed trajectory | Loss, complete model state, and optimizer state bit-exact | `IMPLEMENTATION-ASSUMPTION` + `DERIVED` |
| Machine-readable scope counters | Five synthetic calls; all prohibited counters and formal steps zero | `DERIVED` |

The initial Windows checkpoint test exposed that `os.fsync` cannot use a read-only descriptor on this host; the implementation was corrected to reopen the completed temporary artifact without modifying it. Two independent FP32 formula checks also showed last-bit ordering differences while agreeing numerically; the full installed SGD scalar oracle remains exact, while algebraically independent full-vector checks use declared tight tolerances. All final tests passed after these corrections.

The final fresh environment was installed with the required elevated network permission. A first attempt to run its tests inside that elevated installer context was correctly rejected by Git's dubious-ownership safeguard and produced locale-specific stderr decoding noise. The same installed environment then ran as the normal project user and passed 115/115. The professor-facing result is the normal-user run; no global safe-directory exception was added and no safeguard was disabled.

## Checkpoint guarantees tested

The implementation uses a same-directory temporary artifact, syncs it, reserves a previously unused immutable epoch filename, and atomically replaces only that reservation. Each checkpoint has a strict JSON manifest and SHA256. Resume validates every schema field, model/BN name-shape-dtype/value, all 299 momentum buffers, parameter order, LR/policy IDs, master seed, Python/CPU/requested-CUDA RNG state, source/environment/dataset/config provenance, and manifest identity before mutating the destination model or optimizer.

The rejection corpus includes corrupted bytes; absent/invalid manifest; missing/extra payload and model-state keys; wrong seed/policy/provenance domain; wrong model/optimizer tensor metadata; invalid Python/CPU RNG state; nonzero formal steps; path escape; and immutable-name reuse.

## Deterministic GPU replay

The fresh worker enforced:

- `CUBLAS_WORKSPACE_CONFIG=:4096:8` before Python startup;
- `torch.use_deterministic_algorithms(True)`;
- cuDNN benchmark off and deterministic mode on;
- cuDNN convolution and CUDA matmul FP32 precision policy `ieee`;
- actual Python, PyTorch CPU, and CUDA ambient RNG initialization from the approved domain-separated bundle after isolated model initialization;
- AMP, compile, and recomputation unused.

On the RTX 3070 Ti, three uninterrupted generated steps were compared with a restart from the verified epoch-1 boundary followed by the same two-step suffix. The losses, complete final model state, and complete optimizer state were bit-exact. The stored checkpoint SHA256 identifies that one serialized file. A fresh replay can produce a different archive byte hash because PyTorch embeds the random temporary archive name, while the logical state hashes and trajectory equality remain the reproducibility claims.

## Final commands and results

- Strict combined suite: **115 passed** in 78.34 seconds under `-X dev -W error`.
- Fresh project-external venv reconstructed from the README's locked installation sequence: isolated import and `pip check` passed; the exact current suite passed **115/115** in 87.15 seconds under the normal project user.
- Phase 3 dedicated collection: **54 tests**, all included in the passing final combined suite.
- Source verification: **19 files and five repositories passed**.
- Environment/package syntax: `pip check`, `compileall`, and `git diff --check` passed.

Machine-readable evidence: `evidence/phase3_synthetic_mechanics_2026-08-23.json`.

## Gate

The human approved `phase3_completion_decision_proposal.md` verbatim on 2026-08-23, completing Phase 3. This does not authorize Phase 4 or alter any CIFAR/training/freeze prohibition.
