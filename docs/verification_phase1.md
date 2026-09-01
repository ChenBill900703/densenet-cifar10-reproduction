# Phase 1 verification record

This file preserves the original 27-test milestone exactly as historical context. It is superseded for current verification breadth by `phase1_comprehensive_audit_2026-08-16.md`; the original commit/tag is not moved or rewritten.

## Result and scope

- Final clean verification recorded: **2026-08-16T18:43:32+08:00**.
- Classification: **Phase 1 architecture validation**, not `FORMAL-REPRODUCTION-RESULT`.
- Dataset examples read: **0**.
- Accuracy evaluations performed: **0**.
- Optimizers constructed: **0**.
- Optimizer steps: **0**.

## CPU test suite

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Final result:

```text
Python 3.12.13; pytest 9.0.2; pluggy 1.6.0
27 tests collected
tests/test_architecture.py                 20 passed
tests/test_execution.py                     3 passed
tests/test_initialization_and_batchnorm.py   4 passed
27 passed in 4.13 seconds
```

The suite verifies:

1. exact approved target values and fail-closed configuration checks;
2. 100 counted layers, 99 convolutions, 99 BatchNorm modules, 48 dense units, no Dropout and no Softmax module;
3. the complete `24 -> 216 -> 108 -> 300 -> 150 -> 342` channel trace and spatial trace;
4. prefix-preserving concatenation in every one of the 48 dense units;
5. exact per-stage and per-tensor-class parameter ledgers totaling 769,162;
6. no convolution biases, and a present/zeroed classifier bias;
7. explicit official convolution initialization and historical candidate classifier initialization;
8. exact BatchNorm initial state and a hand-derived two-batch oracle for biased normalization variance, unbiased running variance, momentum direction, and evaluation behavior;
9. test-only seeded construction and initial full-state SHA256 regression;
10. generated-tensor forward/cross-entropy backward with a finite gradient for every trainable parameter;
11. double-precision input gradient checking for a dense unit;
12. an in-memory `torch.save`/`torch.load` serialization round trip after every BatchNorm running-stat buffer has been updated, requiring equivalent logits, parameters, and buffers;
13. fixed 8x8 final pooling and strict `N x 3 x 32 x 32` input rejection.

The test-only initialization seed is `20260816`; it is not a paper seed or a preregistered project reproduction seed. Under the exact pinned Phase 1 environment, the initial full-state SHA256 is:

`4DE22B2BF0305B716FC06671675221F2B56EE586A0FA059D639EE35367772CE4`

The hash includes parameter/buffer names, dtypes, shapes, tensor bytes, and PyTorch's additional `num_batches_tracked` buffers.

## GPU synthetic smoke

Command:

```powershell
.\.venv\Scripts\python.exe scripts\phase1_gpu_smoke.py
```

Observed result:

| Field | Value |
|---|---|
| Classification | `PHASE1-SYNTHETIC-SMOKE-ONLY` |
| Device | NVIDIA GeForce RTX 3070 Ti, compute capability 8.6 |
| PyTorch / runtime / cuDNN | `2.12.1+cu130` / CUDA `13.0` / cuDNN `92000` |
| Trainable parameters | 769,162 |
| Logit shape | `[2, 10]` |
| Finite loss | yes |
| Missing gradients | none |
| Non-finite gradients | none |
| Peak allocated GPU memory | 90,958,848 bytes |
| Optimizer constructed / stepped | no / 0 |

This small generated-tensor check proves only that the selected PyTorch build can execute this graph on the current GPU. It is not the later Phase 4 batch-64 feasibility measurement and must not be extrapolated into a training-time or accuracy claim.

## Environment and source consistency checks

- `python -m compileall -q src tests scripts`: passed.
- `python -m pip check`: `No broken requirements found.`
- All three documented constrained-install commands passed `pip install --dry-run` against the current environment.
- Search for `torch.optim`, `optim.`, and optimizer construction in `src`, `tests`, and `scripts`: no matches.
- Official-source snapshot remained detached and clean at `6d4c8da6a1ef750c9116807b98e7c6265f51d762` during the evidence audit.

## Transparent test-harness corrections before the final clean run

Two development runs exposed errors in newly added assertions, not model discrepancies:

1. A `pytest.raises(..., match=...)` string used an unescaped `+`; the model raised the intended `6N + 4` validation message, but the regular expression did not match. The expected expression was escaped.
2. A module-order assertion expected Python attributes set to `None` to appear in PyTorch's registered child-module dictionary. PyTorch correctly omits those absent Dropout modules; the assertion was corrected to require no registered Dropout and separately require the attributes to be `None`.

After both test-harness corrections, the complete 27-test suite passed cleanly. No model behavior or target value was changed in response to either correction.

An independent read-only code audit then identified that the original round-trip test used only an in-memory Python deep copy and did not first exercise BatchNorm running statistics. Before this milestone was committed, that test was strengthened to perform an actual `torch.save`/`torch.load` byte-stream round trip after one train-mode synthetic forward and to verify all 99 `num_batches_tracked` buffers. The 27-test suite above is the clean rerun after that correction. The same audit also caused the README reconstruction commands to apply the full transitive version snapshot as constraints; missing wheel artifact hashes remain explicitly deferred to Phase 5.

## Remaining gate boundary

Passing this record establishes the implemented Phase 1 contract in the current environment. It does not resolve B-002 through B-006, approve project seeds or aggregation, select the paper-versus-code test cadence, validate CIFAR artifacts, prove full batch-64 feasibility, or create the Phase 5 formal freeze. Those items remain explicit prerequisites before formal optimization.

Independent re-audit disposition: after the serialization and environment-reconstruction findings above were corrected or explicitly scoped, the reviewer reran 27/27 tests and found no remaining architecture/model-math discrepancy. Phase 1 is technically complete, and governance now holds the project before Phase 2.

## Superseding maintenance record

A later same-day comprehensive audit discovered additional isolation/audit defects and gaps in the original tests. These were corrected before any dataset access, optimizer construction, accuracy evaluation, or formal result existed. Both the project environment and a final fresh external reconstruction passed the complete 47/47 suite. The initial full-state hash and 769,162-parameter identity are unchanged. See `phase1_comprehensive_audit_2026-08-16.md` for the findings, corrections, adversarial checks, numerical stress results, and remaining limitations.
