# Phase 1 comprehensive audit and revalidation

## Disposition

- Audit date: **2026-08-16 Asia/Taipei**.
- Classification: **Phase 1 correctness-maintenance and technical revalidation**, not `FORMAL-REPRODUCTION-RESULT`.
- Result: **passed within the authorized Phase 1 scope**.
- Lifecycle consequence: **hold before Phase 2**; this record grants no later-phase permission.
- Dataset examples read: **0**.
- Accuracy evaluations performed: **0**.
- Optimizers constructed: **0**.
- Optimizer steps: **0**.

The original 27-test milestone and tag `phase1-validated-2026-08-16` remain immutable historical evidence. This record supersedes that milestone only as the most comprehensive current verification. No formal result existed, so none was selected, tuned, invalidated, or replaced.

## Findings and corrections

| Finding | Risk | Correction and regression coverage |
|---|---|---|
| Formal model constructors inherited the process-wide default dtype, so changing it to float64 could silently violate the approved FP32 target. | Model configuration isolation | Every formal Conv2d, BatchNorm2d, and Linear construction now explicitly uses CPU and `torch.float32`; the config rejects any other dtype, and a test changes ambient dtype/device to prove isolation. |
| The test-only seeded builder used an all-device seed while only preserving CPU RNG state, so it could alter initialized CUDA RNG streams. | Experimental isolation | The builder now seeds only PyTorch's CPU default generator inside a CPU RNG fork. A CUDA test snapshots every initialized device and requires exact preservation, with an honest skip on non-CUDA hosts. |
| The parameter audit could double-count a shared/tied tensor before detecting it. | Audit correctness | Accounting now fails closed on duplicate tensor identity; adversarial tied and unclassified parameter tests were added. |
| Registration-order assertions did not prove actual pre-activation execution order or exclude train-only graph changes. | Test oracle weakness | Independent functional references now calculate dense-layer `BN -> ReLU -> Conv -> BN -> ReLU -> Conv -> concat` and transition `BN -> ReLU -> Conv -> AvgPool` behavior in both train and eval modes from controlled tensors, then compare every updated state entry. Deliberately wrong activation ordering or train-only output scaling fails. |
| Shape/count tests did not independently prove the stem's zero-padding semantics. | Test oracle weakness | A controlled-weight functional stem oracle now requires exact 3x3, stride-1, dilation-1, group-1, bias-free zero padding and matches an explicit `F.conv2d` reference. A reflect-padding adversary fails it. |
| Absence of an `nn.Softmax` module did not exclude functional post-classifier normalization, and reusing model helpers/component forwards or checking only finite gradients could hide eval-only, train-only, formal-width-conditional, or value-preserving backward changes. | Output/outer-wiring/backward weakness | In both train and eval modes, the expected path uses explicit functional BN/ReLU/Conv/concat/pooling/Linear operations for every formal dense layer, both transitions, and the head. Logits, every updated state entry, input gradients, and all 299 parameter gradients must match the implemented model exactly. Functional Softmax, post-feature scaling, train-only scaling, formal-width-conditional scaling, sum-pooling, and gradient-only scaling adversaries fail. |
| Serialization originally needed stronger stateful coverage. | Checkpoint auditability | The existing round-trip test performs a real `torch.save`/`torch.load` byte-stream cycle after all 99 BatchNorm counters advance, then requires exact logits, state hash, parameters, and buffers. |
| Package tests could import directly from `src` and therefore did not independently prove the editable installation. | Environment reconstruction | An isolated `python -I` process outside the repository must resolve exactly this checkout's installed package, version, declared torch dependency, and torch build. |
| Source/PDF integrity and nested repository state were documented but not automated. | Evidence traceability | `evidence/source-lock.json` and `scripts/verify_sources.py` now verify 17 file hashes plus five repository commits, remotes, clean detached state, and Git object integrity. |

The first three rows are real correctness/audit defects. They did not change the approved architecture tensors under the recorded normal construction path: the independent parameter total remains **769,162**, and the initial full-state SHA256 remains:

`4DE22B2BF0305B716FC06671675221F2B56EE586A0FA059D639EE35367772CE4`

## Superseding automated suite

The audit suite contains **47 tests**:

| Test area | Count | Principal coverage |
|---|---:|---|
| Architecture | 25 | target/config fail-closed rules, dtype/device isolation, census, shapes, parameter ledgers, concatenation, train/eval outer graph, raw logits, input guards |
| Evidence integrity | 1 | PDFs/source files and five nested repository locks |
| Execution | 3 | finite forward/backward, gradcheck, stateful save/reload |
| Independent functional oracles | 5 | stem padding plus train/eval dense-unit and transition execution/state behavior |
| Initialization and BatchNorm | 10 | initializer, state hash, CPU/CUDA RNG isolation, seed validation, analytic BatchNorm semantics |
| Packaging/environment | 3 | isolated installed import, exact live lock, package-index policy |
| **Total** | **47** | |

Observed project-environment result:

```text
python -X dev -W error -m pytest -q
47 passed
```

Warnings are promoted to errors. The evidence verifier independently reported five repositories, 17 locked files, and zero errors. `pip check` reported no broken requirements.

## Clean reconstruction

A second, project-external virtual environment was created from the documented four-file installation sequence after all dependency-layout changes:

1. constrained bootstrap packages from PyPI;
2. constrained ordinary runtime dependencies from PyPI;
3. exact CUDA 13.0 PyTorch/TorchVision wheels with `--no-deps` from the official PyTorch index;
4. constrained test dependencies from PyPI;
5. the current checkout as an editable `--no-deps --no-build-isolation` install.

In that fresh environment, `pip check`, syntax compilation, the isolated installed-package assertion, the exact 20-distribution live-lock comparison, the evidence/source check, and the final complete **47/47** suite passed. This is a host reconstruction result, not a wheel-artifact supply-chain freeze; artifact SHA256 values remain a Phase 5 prerequisite.

## Independent numerical stress audit

The broad stress pass was a **one-time independent read-only reviewer observation**, not part of the 47-test suite and not automatically replayed by one committed command. Its recorded case and measurement summary is preserved in `evidence/phase1_numerical_stress_observation_2026-08-16.json`; this limitation must remain attached to the claims.

Generated tensors only were used. CPU and GPU batches 1, 2, 4, and 8 produced finite logits, losses, and gradients for all 299 trainable tensors. The reviewer checked all 99 BatchNorm counters and train/eval state behavior; strict missing/extra state-key rejection; stateful serialization; CPU/GPU and FP32/FP64 round trips; CPU/GPU anomaly detection; non-contiguous input; and zero, one, bounded `[-3,3]`, normal-times-10, and normal-times-1000 inputs. A 30-inference CPU loop had only 12,288 bytes of sampled RSS range/final drift after warm-up. On GPU, 50 inference iterations held allocated/reserved memory exactly at 20,426,752/50,331,648 bytes, and 15 backward iterations held it exactly at 20,427,264/115,343,360 bytes. These observations support finite/stable Phase 1 execution on this host; they are not a training-feasibility or leak-proof guarantee for later phases.

The GPU default-policy diagnostic exposed an important unresolved governance issue:

- ambient deterministic algorithms: disabled;
- ambient cuDNN deterministic mode: disabled;
- ambient convolution precision: TF32 enabled;
- `scripts/phase1_determinism_diagnostic.py` now makes the fresh-process evidence reproducible: it records three ambient-default and three explicit deterministic-candidate generated-tensor runs, including every state/logit/gradient hash and all relevant settings;
- in the recorded 2026-08-16 execution, all three ambient-default processes had logits hash `8A0AD741AF3C66ECB282DE2F54668B6D2F55EB619207C945BE49D79125BF43AD`, post-forward state hash `0F35E978FC70E188845382DF49E04B87C41C32355CDAD91E35D350F5F6351E96`, and loss `2.310762882232666`, but three different complete-gradient hashes: `94767F991CE2936F32F78DF3400F5862EB0552D637D707D91F0AA0AD122F0CB0`, `9741CEC3AB96AF8BDE567A2F6EA39B7C28639F9A4C066A3AE6F83721347948C5`, and `9C365BA6767272FF46E960FD42490562D25364A2F1D2787352FDB5556C706661`;
- under the diagnostic deterministic/TF32-disabled candidate (`CUBLAS_WORKSPACE_CONFIG=:4096:8`, deterministic-algorithm enforcement enabled, benchmark disabled, convolution/matmul precision set to IEEE), all three processes reproduced gradient hash `F012DCBBF94562CE6EEDE8EECB91C0B14F9E012AB26929AADC7106434C07F912`, logits hash `1D3CDA00D9C71E3482006C663C27F3225650358BF2C455BE8277BD9BA91B9C7B`, post-forward state hash `E17BEABABBCCAA6CCCA6EB3EBD858EC213486820F2B794F1ECFA6F76584F082A`, and loss `2.3107123374938965`;
- A committed paired diagnostic now defines the reported relative error as `max(abs(a-b)) / max(max(abs(b)), 1.0)`, reduced across all batch/class logits. It uses the same model seed 28000, input seed 28001, input tensor, weights, CPU reference, and IEEE matmul setting for both CUDA convolution modes. Run `scripts/phase1_precision_diagnostic.py` to reproduce the values and raw-output hashes; this avoids treating unrelated seeds as a controlled comparison.

The committed paired diagnostic reproduced the following same-input, same-weight observations over 30 FP32 logits:

| Comparison | Maximum absolute error | Reference maximum | Defined relative infinity error |
|---|---:|---:|---:|
| CUDA TF32 convolution vs CPU | 157.625 | 395,162.1875 | `3.9888684946608156e-4` |
| CUDA TF32-disabled convolution vs CPU | 1.15625 | 395,162.1875 | `2.9260137649177276e-6` |
| CUDA TF32 convolution vs CUDA TF32-disabled | 158.5 | 395,161.03125 | `4.0110230378390837e-4` |

The machine-readable outputs, including unabridged hashes and all settings emitted by these diagnostics, are committed as `evidence/phase1_determinism_diagnostic_2026-08-16.json` and `evidence/phase1_precision_diagnostic_2026-08-16.json`. Driver/OS identity is recorded separately in `environment_phase1.md`; neither diagnostic claims a Phase 5 machine freeze. The ambient gradient hashes are observations from that dated execution and are expected to change on another nondeterministic replay; the diagnostic conclusion depends on their inequality, not on reproducing those particular three values.

This is not classified as a Phase 1 model defect. It is direct evidence that A-003/B-004/C-006 is trajectory-changing and must remain a human-approved blocker before formal freeze. The GPU smoke script disables TF32 only for its finite forward/backward diagnostic and explicitly makes no determinism or strict-IEEE claim.

## Evidence and portability limits

- The user PDF, publication comparison PDF, and five forensic source clones are outside the root Git tree. The machine verifier checks them on this host, but a fresh clone must reconstruct or provide those inputs before the full evidence test can pass. Another host may set `DENSENET_USER_PAPER_PATH` for the same hash-verified primary PDF; the forensic repositories still belong at the locked relative `sources/` paths.
- Post-record maintenance note (2026-08-23): the user restored the exact 1,142,400-byte PDF with the same locked SHA256, and it is now tracked at `docs/1608.06993v5.pdf`. The preceding bullet describes the original 2026-08-16 milestone state; the forensic source clones remain external.
- The root repository currently has no Git remote or off-machine backup. Local commits and tags provide history, not offsite preservation.
- Exact package versions are locked and reconstruct successfully, but the Python interpreter executable and wheel artifact hashes are not yet frozen.
- The authors' actual historical cuDNN build and reduction order remain `UNKNOWN`.
- CIFAR artifact identity, DataLoader behavior, optimizer/scheduler behavior, batch-64 full-run feasibility, seeds, aggregation, checkpoint selection, and final-test policy have not been validated or approved.

## Gate conclusion

No remaining architecture or model-math discrepancy was found after correction and adversarial re-testing. Phase 1 remains technically validated. The comprehensive audit does **not** resolve B-002 through B-006, A-003, C-001, C-005, or C-006; does not freeze Phase 5; and does not authorize Phase 2, CIFAR access, an optimizer, or training.

This exact correctness-maintenance snapshot is identified by annotated tag `phase1-revalidated-2026-08-16`. The earlier `phase1-validated-2026-08-16` tag remains unchanged as the historical 27-test milestone. Neither tag is a formal-result or Phase 5-freeze marker.
