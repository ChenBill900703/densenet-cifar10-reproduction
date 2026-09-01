# Phase 5 Entry and Freeze-Assembly Decision Proposal v1

Status: **APPROVED 2026-08-23 / HISTORICAL ASSEMBLY AUTHORITY / SUPERSEDED BY D-020 FORMAL FREEZE**

Date prepared: **2026-08-23**

## 1. Purpose and current boundary

Phases 1-4 are complete. Phase 5 must convert the approved, tested candidates
into one immutable and independently reconstructible formal baseline. This
document proposes authority to assemble and validate that freeze candidate; it
does not itself freeze anything and does not authorize a formal optimizer step.

Until the exact authorization in section 8 is approved, the project must not
download or assemble formal dependency artifacts, implement a formal runner,
create a freeze manifest, enter Phase 5, decode CIFAR for model execution, or
construct a new training trajectory.

Even after entry approval, Phase 5 technical output will require a separate
human completion/freeze decision. A later Phase 6 entry decision will be
required before the first formal optimizer step.

## 2. Already approved configuration candidates

These values are evidence-backed or previously human-approved. Phase 5 would
encode them exactly; it may not reinterpret them.

| Domain | Candidate to encode | Classification / authority |
|---|---|---|
| Target | DenseNet-BC-100-12 / CIFAR-10+ / FP32 / physical batch 64 / 300 epochs | Target approval; paper/code-backed |
| Architecture | 100 counted layers; k=12; bottleneck 4k; theta=0.5 floor; 769,162 trainable parameters; no convolution bias; dropout 0 | Paper/code/derived; Phase 1 validated |
| Initialization | Conv fan-out normal; BN 1/0 and running 0/1; classifier uniform `±1/sqrt(342)`, bias 0 | A-005/A-006 approved |
| Dataset | Toronto binary archive SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD` | A-007 approved |
| Train data | all 50,000 records; official rounded normalization; flip p=0.5; normalized-zero pad 4; crop offsets 0..8; workers 2 | Phase 2 approved/validated |
| Train partition | 782 batches/epoch: 781x64 plus one x16; no accumulation | Paper/code/derived; A-008 approved |
| Optimizer | one ordered 299-tensor SGD group; lr 0.1; momentum 0.9; Nesterov; dampening 0; coupled decay 1e-4 on all tensors; foreach/fused off | A-009 approved/validated |
| LR | epochs 1-149: 0.1; 150-224: 0.01; 225-300: 0.001; no scheduler object | H-004 approved/validated |
| Loss/order | raw logits; unweighted mean cross-entropy; zero-grad -> forward -> loss -> backward -> finite checks -> step | M-004 approved/validated |
| Runtime | eager FP32; deterministic algorithms; cuDNN benchmark off/deterministic on; convolution/matmul IEEE; AMP/TF32/compile/recomputation off | A-003/A-011 approved/validated |
| Checkpoint | immutable atomic checkpoint after every completed epoch; unfinished epoch rolls back to prior boundary | A-012 approved/validated |
| Seeds | `1021082110`, `1747066946`, `869460408`, in this fixed order; approved SHA256 runtime/data domains | A-002/A-010/H-003 approved/validated |
| Test | only after all three training trajectories are complete and hash-locked; each seed once at epoch 300; 10,000 sequential records; batch64/workers0; normalization only | A-004/M-002 plus proposed stricter ordering below |
| Reporting | every seed; integer incorrect count and error; arithmetic mean primary; sample standard deviation descriptive; compare honestly with paper 4.51% | A-002/A-004 approved; exact schema proposed below |

The actual formal source commit, project-wheel SHA256, Python-runtime archive
SHA256, third-party wheel SHA256 set, canonical config SHA256, and freeze
manifest SHA256 do not exist yet. They are Phase 5 outputs and must never be
invented or filled with the current HEAD by assumption.

## 3. Proposed implementation assumptions

### A-015 - Canonical identity and serialization

Adopt the ASCII target slug:

`densenet-bc-100-12__cifar10-plus__fp32__b64__e300`

Canonical JSON artifacts use UTF-8, LF, sorted keys, no insignificant
whitespace, ASCII escaping, and one terminal LF. Hashes are uppercase SHA256 of
the exact bytes. Human-readable Markdown is explanatory and never the source of
the frozen hash.

The canonical configuration contains only trajectory/reporting values. The
separate freeze manifest binds that config SHA256 to source, environment,
dataset, runner, and artifact identities, avoiding a self-referential commit
hash inside the config.

### A-016 / H-009 - Offline-reconstructible software supply chain

The current version lock is not artifact-immutable. Phase 5 therefore must:

1. download exactly one wheel for every entry in `environment-lock.txt`, from
   the already approved PyPI or official PyTorch index and for CPython 3.12
   Windows x86-64;
2. store the wheels under an ignored, read-only formal wheelhouse and commit a
   filename/byte-count/SHA256/index-origin manifest;
3. build exactly one non-editable project wheel from the later freeze-source
   candidate commit and record its byte count and SHA256;
4. archive the complete host Python base runtime used to create the venv,
   commit a per-file hash manifest, and record the archive SHA256;
5. prove a project-external environment can be created offline with
   `--no-index`, the exact wheelhouse, hash enforcement, and the frozen project
   wheel; `pip check`, isolated import, installed-file RECORD verification, and
   the complete suite must pass;
6. record Windows build, Python build, driver 591.86, GPU UUID, compute
   capability, PyTorch/CUDA/cuDNN, deterministic flags, and every installed
   distribution/file hash.

The current observed venv launcher SHA256
`560B9EF7D856608AB8DA02DED2DC8A1951AD1F424C382C0EC6A698874165A18E`
and base `python.exe` SHA256
`D8E3F0ADF246DB00358C0C4ED349CF714898178F9558FB0E944F79F5C07F8EAA`
are planning observations only. The complete archived runtime manifest—not
either executable alone—would be the freeze identity.

### A-017 / H-011 - Two-commit source and freeze-record identity

Avoid a circular manifest:

1. create a **freeze-source candidate commit** containing the final runtime
   package, formal runner, canonical config, schemas, and tests;
2. build the project wheel and a Git bundle containing that candidate commit;
3. generate all artifact hashes and the freeze manifest;
4. commit only the resulting evidence/manifest as a later **freeze-record
   commit**;
5. present both commits, all artifact hashes, and the manifest SHA256 in a
   Phase 5 completion proposal.

Formal execution would use only the project wheel built from the freeze-source
candidate. The later record commit is governance evidence and cannot silently
change runtime code. The formal freeze tag must not be created until the human
accepts the completion package.

### A-018 / M-007 - Train-all-then-test execution order

Each seed trains in a fresh process, sequentially in the listed order. The
formal runner must not open or decode any test record during training. All three
epoch-300 checkpoints must first be complete, hash-verified, and marked
immutable. Only then may a later Phase 6 evaluation stage test each seed once,
in the same seed order.

This is stricter than merely testing after each individual run and prevents any
observed test result from influencing later training operations. No validation,
best epoch, best seed, early stopping, or result-dependent retry exists.

If a final-test attempt is interrupted before all 10,000 samples complete, the
incident and partial attempt are preserved and execution stops for a new human
decision; it is not silently rerun and described as a single evaluation.

### A-019 / H-010 - Append-only formal attempt accounting

The formal runner must distinguish:

- accepted trajectory steps: exactly 234,600 for each completed seed;
- physical optimizer-call **intents**, durably written and fsynced immediately
  before `optimizer.step()`;
- completed optimizer calls, durably written after the call;
- rolled-back calls from an interrupted epoch;
- unresolved pre/post-step crash windows.

An append-only SHA256 hash chain lives outside rollback checkpoints. It is never
truncated when an epoch is rerun. If a hard crash leaves an intent without a
completion record, the project reports a lower/upper bound rather than
inventing an exact physical-call count. Clean executions must have no unresolved
intent and exact counts. `formal optimizer steps` can no longer remain zero
after Phase 6 begins, even for later-invalidated or rolled-back attempts.

### A-020 / M-006 / M-008 - Immutable run and result artifacts

After freeze, use this ignored runtime layout:

`runs/formal/<FULL_FREEZE_MANIFEST_SHA256>/seed-<MASTER_SEED>/`

Every path is create-new/no-overwrite. Retain all 300 epoch checkpoints and
manifests per seed, training logs, attempt ledger, launch/environment reports,
final-evaluation artifact, and aggregation artifact. Before Phase 6, Phase 5
must derive the actual checkpoint byte size with a schema-faithful structural
fixture, including representative momentum tensors but never invoking
`optimizer.step()`, calculate required storage for 900 checkpoints plus 20%
operational headroom, and fail closed if free disk is below that recorded
requirement.

Per-seed final results store the integer incorrect count out of 10,000 as the
primary exact observation. Error percent is exactly `incorrect/100`; retain the
integer and decimal without binary-float-only serialization. The aggregate
stores all three integers, every two-decimal individual error, the exact
rational arithmetic mean, a decimal rendering with at least four places, and
sample standard deviation with its formula and at least six decimal places.
There is no success threshold against 4.51%, no confidence-interval claim with
three project seeds, and no hidden rounding or best-run selection.

### H-012 - Exact launch identity and fail-closed external state

Every later formal process must fail before CIFAR decode/model construction
unless the freeze manifest, installed project wheel, complete distribution and
RECORD hashes, Python runtime, source/config/dataset hashes, Windows build,
driver, exact GPU UUID/capability, deterministic flags, and run directory all
match. Record free disk, free/total VRAM, WDDM state, and other GPU compute
processes.

No universal VRAM threshold is invented. Another compute process, identity
mismatch, insufficient derived disk headroom, OOM, non-finite state, ledger
mismatch, or artifact mutation stops the run. The runner must not close user
applications, change batch/precision/graph settings, or retry automatically.

## 4. Proposed Phase 5 technical scope

Entry approval would permit only:

- implement the canonical config, freeze manifest/schema, formal runner,
  checkpoint/result schemas, hash-chain attempt ledger, and fail-closed launch
  checks;
- download and hash the exact dependency wheels; archive/hash the Python
  runtime; build/hash the candidate project wheel and source Git bundle;
- hash/reverify the approved CIFAR archive without decoding it for a model;
- create an offline project-external reconstruction and run regression/static
  tests;
- use mock/fake orchestration and structural tensors that never call an
  optimizer for new Phase 5 runner tests;
- rerun the existing approved regression suite, whose generated-only Phase 3
  mechanics tests remain non-formal test executions and are reported
  separately from the Phase 5 freeze assembly.

Entry approval would still prohibit:

- any CIFAR model forward, loss, backward, optimizer step, training, test
  decode/evaluation, prediction/argmax, accuracy/error, or result aggregation;
- any new Phase 5 optimizer diagnostic, even on generated tensors;
- pretrained results;
- creation of a formal freeze tag;
- Phase 6 entry or a formal optimizer step.

Formal optimizer steps remain **0** throughout Phase 5 assembly.

## 5. Mandatory Phase 5 acceptance obligations

1. One canonical config passes independent schema/value/hash reconstruction for
   every approved trajectory and reporting setting.
2. One freeze manifest binds the candidate source commit, project wheel,
   source bundle, config, dataset, complete wheelhouse, Python runtime archive,
   primary-paper/source-lock identities, OS/GPU/driver/runtime identities,
   policies, schemas, and test evidence.
3. Every referenced artifact exists, is a regular non-symlink file inside its
   approved root, has exact bytes/SHA256, and rejects one-byte mutation,
   missing/extra files, path escape, duplicate identities, and case collision.
4. Offline fresh-environment reconstruction passes with network disabled and
   proves the installed package came from the frozen project wheel, not `src/`
   or an editable install.
5. Formal launch validation rejects every wrong source/config/dataset/wheel/
   Python/environment/OS/driver/GPU/policy/run-id condition before model or
   dataset construction.
6. Static and mock execution tests prove train-all-then-test ordering, no test
   access during all training stages, exactly three fixed seeds, no result-
   dependent branch, and fail-closed interrupted evaluation.
7. Attempt-ledger mutation/crash-window tests prove append-only hash chaining,
   no rollback truncation, conservative unresolved-step reporting, and exact
   clean-run counts without calling an optimizer.
8. Checkpoint/result schemas reject prediction, best-model, validation,
   accuracy-during-training, nonzero test access during training, and any
   omitted provenance/scope/hash field.
9. Storage projection and disk gate are derived and recorded without deleting
   earlier evidence or changing the approved retention rule.
10. The complete current regression suite passes in the project environment.
    The offline wheel environment passes the same behavioral suite under an
    explicit formal-wheel import mode plus source verifier, `pip check`,
    compilation, locked installed-file/RECORD audit, isolated import from
    outside the checkout, and clean-tree checks; tests must prove that neither
    editable installation nor `pyproject` source-path injection masked the
    frozen wheel.
11. A machine-readable Phase 5 assembly report shows zero CIFAR model calls,
    zero CIFAR loss/backward/optimizer/prediction/accuracy/test operations, zero
    new Phase 5 optimizer diagnostics, and zero formal optimizer steps.
12. A separate completion package presents the freeze-source commit,
    freeze-record commit, full manifest SHA256, artifact/storage identities,
    test counts, residual limitations, and exact freeze decision language.

Passing these obligations would technically assemble a freeze candidate only.
No freeze exists until the human approves the later completion package, and no
formal run may begin without a later Phase 6 entry decision.

## 6. Residual limitations that remain visible after a freeze

- Authors' paper seeds, independent-run count, exact Torch/cuDNN binaries, and
  floating-point reduction trajectory remain `UNKNOWN`.
- The project freezes a human-approved semantic PyTorch port, not bitwise
  reconstruction of the authors' private machine.
- The root repository currently has no off-machine remote. A hashed Git bundle
  improves portable audit evidence but is not an offsite backup unless the
  human separately places a copy elsewhere.
- Windows/WDDM/display contention can change timing. Accuracy is the formal
  scientific result; runtime is reported operational evidence.
- Three preregistered project seeds do not justify a population confidence-
  interval claim.

## 7. Recommended identifiers if approved

| ID | Proposed decision |
|---|---|
| A-015 | Canonical ASCII target slug and canonical JSON/hash serialization |
| A-016 / H-009 | Complete offline wheelhouse plus Python-runtime artifact freeze |
| A-017 / H-011 | Two-commit freeze-source/freeze-record identity without circular hashes |
| A-018 / M-007 | Train all three immutable trajectories before any final-test access |
| A-019 / H-010 | Append-only intent/completion attempt ledger and honest crash-window bounds |
| A-020 / M-006 / M-008 | Immutable run layout, checkpoint retention, exact result/aggregation schema, derived disk gate |
| H-012 | Exact launch identity and fail-closed external-state policy |
| L-001 | `densenet-bc-100-12__cifar10-plus__fp32__b64__e300` |

All are `IMPLEMENTATION-ASSUMPTION` policies proposed for the project. None is
claimed to be a missing paper setting.

## 8. Exact proposed authorization

**「我批准 Phase 5 entry and freeze-assembly decision package v1：批准 A-015/L-001 的 canonical target slug `densenet-bc-100-12__cifar10-plus__fp32__b64__e300` 與 canonical JSON/SHA256 規則；批准 A-016/H-009 的完整 wheelhouse、non-editable project wheel、Python runtime archive 與 offline hash-enforced reconstruction；批准 A-017/H-011 的 freeze-source candidate commit 與 freeze-record commit 雙重身分；批准 A-018/M-007 固定依序完成三個 project seeds 的全部 epoch-300 training artifacts 後才允許任何 final-test access；批准 A-019/H-010 的 append-only pre-step intent/post-step completion hash-chain ledger、rollback 不截斷與 crash-window 誠實上下界；批准 A-020/M-006/M-008 的 full-manifest-hash run layout、保留每 seed 300 個 checkpoints、derived disk gate、integer incorrect-count primary result 與 exact mean/sample-SD schema；批准 H-012 exact launch identity 與 fail-closed external-state policy；開始 Phase 5 freeze-candidate assembly。Phase 5 僅可實作與靜態/mock 驗證 runner/schema/ledger、下載並 hash 依賴工件、建立 offline fresh environment、reverify dataset hash，以及執行既有 generated-only regression tests；仍禁止任何 CIFAR model forward、loss、backward、optimizer step、training、test decode/evaluation、prediction/argmax、accuracy/error、result aggregation、新的 Phase 5 optimizer diagnostic、pretrained results、formal freeze tag、Phase 6 與正式 optimizer step；formal optimizer steps 維持 0。Phase 5 技術完成後仍須另行批准 completion/freeze package，且正式訓練仍須另行批准 Phase 6 entry。」**

## 9. Status before human decision

`PHASE 4 COMPLETED - PHASE 5 ENTRY/FREEZE-ASSEMBLY DECISION PENDING`
