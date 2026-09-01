# Open Questions and Phase Gates

No `BLOCKER` may be silently downgraded. Current disposition: **D-057 completed all three formal runs, single final tests, and frozen aggregation; D-058 completed the primary-evidence comparison; D-059 completed the professor-defense delivery; D-060 closed the project. No unresolved blocker remains, and no further work is authorized within the approved target lifecycle.**

H-020 was corrected and accepted by D-045. The professor's one-week deadline
was incompatible with the old frozen ledger's full-history-per-append cost.
D-043 preserves that old namespace, while the corrected new namespace completed
all three seeds from epoch 1 and is the sole source of D-057 results.

The human approved `phase6_preflight_acl_corrective_assembly_decision_proposal.md` verbatim as D-030 and the completion package verbatim as D-034. H-016 through H-019 are accepted for the new freeze; a separately prepared Phase 6 re-entry approval remains mandatory.

## RESOLVED

| ID | Question | Resolution evidence | Scope of resolution |
|---|---|---|---|
| B-001 | Which exact model/dataset/augmentation cell is the primary formal target? | On 2026-08-16 the human stated exactly **「我批准此 DenseNet formal target」** after the recommendation of DenseNet-BC-100-12 / CIFAR-10+ / FP32 / batch 64 / 300 epochs. | `RESOLVED - TARGET APPROVED`. Does not resolve B-002 through B-006, approve their assumptions, freeze Phase 5, or authorize training. |
| B-002 | Final epoch/one-time test or public-runner best test epoch? | Human approval of Phase 2 entry decision package v1 on 2026-08-16. | `RESOLVED - PAPER-FAITHFUL POLICY APPROVED`: test each seed exactly once after epoch 300; never select a best-test epoch. Implementation/freeze validation remains. |
| B-003 | What independent-run count, seed count, seed values, and aggregation statistic will be preregistered? | Human approval of the SHA256-derived seed and reporting policy in Phase 2 entry decision package v1, followed by H-003 approval in D-010 and freeze approval in D-020. | `RESOLVED / FROZEN`: three seeds `1021082110`, `1747066946`, `869460408`; report every run, arithmetic mean primary, sample standard deviation descriptive; never select best seed. |
| B-004 | Which deterministic policy should the PyTorch port use? | Human approval plus Phase 1 diagnostics, Phase 3 deterministic checkpoint replay, and D-020. | `RESOLVED / TESTED / FROZEN`: deterministic algorithms, TF32/AMP/compile disabled, IEEE FP32 policy, benchmark off/deterministic on. |
| B-005 | What exact BatchNorm mapping should the modern port freeze? | Human approval of A-005 and its analytic/exact acceptance oracles. | `RESOLVED - HISTORICAL SEMANTIC ORACLE APPROVED`; no bitwise claim about the authors' unknown cuDNN binary. |
| B-006 | What exact classifier weight initialization should the port freeze? | Human approval of A-006. | `RESOLVED - HISTORICAL CANDIDATE ADOPTED`: uniform `±1/sqrt(342)`, bias zero; exact tests remain mandatory. |
| A-007 / H-001 / M-001 | Which CIFAR-10 archive becomes the sole formal dataset artifact? | Human approval of Phase 2 completion decision package v1 on 2026-08-23 after full cross-format verification; D-020 freeze. | `RESOLVED / FROZEN`: Toronto binary SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD`; Python archive is equivalence evidence only. |
| H-003 | What worker count and epoch-to-data RNG mapping is adopted? | D-010 plus complete 50,000-sample workers 0/2 bit-exact replay; D-020 freeze. | `RESOLVED / FROZEN`: domain `densenet-cifar10-loader-v1`, explicit global decisions, training workers 2. |
| M-002 | Exact evaluation batch size and worker count? | D-010 plus complete 10,000-example diagnostic. | `RESOLVED`: batch 64, workers 0, sequential order, normalization only. |
| M-003 | Preserve official rounded normalization constants or recompute? | D-010 and official code evidence. | `RESOLVED`: preserve mean `[125.3,123.0,113.9]` and std `[63.0,62.1,66.7]` exactly. |
| H-004 | How will end-of-epoch LR boundaries map into PyTorch scheduler calls? | D-012 approval plus Phase 3 boundary/rejection tests. | `RESOLVED / TESTED`: no scheduler object; explicit function maps 1-149/150-224/225-300 to 0.1/0.01/0.001. |
| H-005 | Does a memory-saving implementation reproduce the baseline? | D-012 deliberately rejected an alternate path; Phase 3 report records eager execution without recomputation/compile/AMP. | `RESOLVED FOR BASELINE`: no alternate path; exact batch-64 feasibility remains H-002. |
| H-006 | What checkpoint/resume granularity is required? | D-012 plus strict mutation corpus and bit-exact deterministic GPU rollback replay. | `RESOLVED / TESTED`: immutable atomic epoch boundary, prior-boundary rollback, no mid-epoch resume. |
| H-007 | How do master seeds map to runtime RNGs? | D-012 plus all-three-seed domain replay and GPU checkpoint restoration. | `RESOLVED / TESTED`: preregistered SHA256 domains with epoch/device separation. |
| M-004 | Exact loss and update order? | D-012 plus independent value/gradient and full-model step tests. | `RESOLVED / TESTED`: raw logits, unweighted mean cross-entropy, no smoothing/accumulation, explicit gradient/state validation. |
| H-008 | How is a Phase 4 capacity result classified without inventing a universal safety margin? | D-015 policy and D-017 completion approval. | `RESOLVED FOR PHASE 4`: `OBSERVED-FIT` accepted with exact headroom shown and no universal threshold claim. |
| M-005 | What exact Phase 4 memory/timing fields and interval are reported? | D-015 policy, D-016 evidence and D-017 acceptance. | `RESOLVED FOR PHASE 4`: 66 stage/per-step byte records and ten synchronized update timings accepted. |
| H-002 | Can the approved model keep batch 64 in FP32 on the exact RTX 3070 Ti under the approved eager implementation? | D-016 technical evidence plus D-017 human acceptance. | `RESOLVED FOR PHASE 4`: `OBSERVED-FIT`; peak allocated 2,336,236,544 bytes and peak reserved 2,680,160,256 bytes; not a formal-run guarantee. |

## PHASE 5 BLOCKERS RESOLVED AND FROZEN

Phase 5 entry package v1 approved the following dispositions for technical assembly. Their evidence passed, and D-020 froze every item below.

| ID | Freeze question | Frozen disposition |
|---|---|---|
| H-009 | How are exact dependency and Python runtime bytes frozen and reconstructed offline? | Complete hashed wheelhouse, non-editable project wheel, archived Python runtime, offline hash-enforced fresh reconstruction. |
| H-010 | How are formal optimizer calls counted across rollback and a hard crash between GPU and disk operations? | Append-only pre-step intent/post-step completion hash chain; preserve rollback calls and report unresolved intent bounds. |
| H-011 | How can source and a committed freeze manifest be bound without circular commit hashes? | Freeze-source candidate commit plus later evidence-only freeze-record commit. |
| H-012 | What exact runtime/external-state launch checks stop a formal process before mutation? | Full manifest/software/OS/driver/GPU/policy/run-root verification; fail closed with no workaround. |
| M-006 | What exact final result and aggregation schema is frozen? | Integer incorrect counts, exact decimal/rational mean, sample SD formula, all individual runs, no threshold/selection. |
| M-007 | When may test data first be accessed across three runs? | Only after all three epoch-300 training artifacts are immutable; each seed once in fixed order. |
| M-008 | What checkpoint retention and disk gate applies? | Retain 300 per seed; derive actual requirement plus 20% headroom before Phase 6. |

## FORMAL EXECUTION GATES CLOSED

The D-046 superseding entry, fresh exact-account preflight, three ordered formal trainings, three fixed-order single final tests, and frozen aggregation all completed. The original failures and older namespaces remain immutable historical evidence and are not result inputs.

| ID | Phase 6 readiness blocker | Required disposition |
|---|---|---|
| H-013 | Frozen CLI has no legal epoch-1 initial-boundary rollback path after interruption. | `RESOLVED / FROZEN BY D-024`: ledger-preserving, fail-closed initial-boundary resume passed static/mock tests. |
| H-014 | Frozen runner permits seed 2 or seed 3 to start before earlier seeds complete. | `RESOLVED / FROZEN BY D-024`: fixed seed order is enforced before model/data construction. |
| H-015 | Authorization accepts arbitrary SHA256-shaped decision hashes without hashing the named decision files. | `RESOLVED / FROZEN BY D-024`: canonical decision files are schema/hash/freeze verified before mutation. |
| H-016 | The approved launch account `<REDACTED_EXECUTION_ACCOUNT>` could not traverse the prepared CIFAR directory. | `RESOLVED / FROZEN BY D-034 / EXECUTED`: minimal read/traverse ACL correction preserved every data byte/hash; exact-account replay and final formal execution passed. |
| H-017 | Preflight did not verify prepared training access/integrity before mutation. | `RESOLVED / FROZEN BY D-034 / EXECUTED`: before-mutation guards passed and governed every final formal launch. |
| H-018 | Train verification could read `test_batch.bin` before all training completed. | `RESOLVED / FROZEN BY D-034 / EXECUTED`: training-only verifier touched five train batches; test bytes remained gated until D-053. |

## MEDIUM

No unresolved medium-impact Phase 4 entry question remains.

## LOW

| ID | Question | Note |
|---|---|---|
| L-001 | Human-facing target naming convention | Frozen as `densenet-bc-100-12__cifar10-plus__fp32__b64__e300` by D-020. |
| L-002 | Markdown/PPT visual style for the final defense | `RESOLVED BY D-059`: restrained Codex Grid visual system, Traditional Chinese professor-facing copy, 14-slide rendered/verified PPTX. |
