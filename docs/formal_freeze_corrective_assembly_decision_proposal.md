# Formal-Freeze Corrective Assembly Decision Proposal v1

Status: **APPROVED / TECHNICALLY VALIDATED 2026-08-24 / COMPLETION DECISION PENDING / PHASE 6 FORBIDDEN**

Date prepared: **2026-08-23**

## Decision disposition

The human authorized a narrowly scoped, generated/static/mock-only correction
of H-013, H-014, and H-015 from the Phase 6 entry readiness audit. This is not
Phase 6 entry and grants no CIFAR model execution or optimizer authority.

## Why a corrective freeze is required

The first formal freeze was created before any formal optimizer step, so no
training result is invalidated. The readiness audit found that the frozen CLI
cannot legally restart an interrupted first epoch, does not enforce formal seed
training order, and does not hash-verify the two decision artifacts named by
its authorization file. These are execution-governance defects in a still
unexecuted runner, not architecture, dataset, or paper-protocol changes.

## Authorized correction scope if approved

1. Implement a fail-closed initial-boundary resume path that preserves the
   existing append-only ledger and permits deterministic epoch-1 rollback only
   under the exact H-013 conditions.
2. Enforce seed order `1021082110`, `1747066946`, `869460408` before any new or
   resumed formal seed process constructs a model or dataset.
3. Add closed canonical Phase 5-completion and Phase 6-entry decision record
   schemas; require their files at launch and verify their exact SHA256 values
   against the canonical authorization JSON and frozen manifest identity.
4. Add mutation, negative-path, fresh-process, packaging, offline-wheel, and
   exact-launch tests for the three corrections. Tests may use temporary files,
   generated tensors, fake callbacks, and monkeypatches only. They may not use
   CIFAR model forward/loss/backward/optimizer/test evaluation.
5. Rebuild the non-editable project wheel and every affected evidence manifest,
   repeat offline hash-enforced reconstruction, and produce a new machine report,
   freeze-source commit, freeze-record commit, manifest hash, and proposed
   superseding annotated tag.

The canonical model, dataset archive, data semantics, optimizer mathematics,
learning-rate schedule, seeds, evaluation rule, result schema, batch size,
precision, and all other frozen scientific settings must remain byte/semantic
identical unless an unavoidable identity field changes because the corrected
wheel/source is rehashed.

## Required acceptance conditions

- a regression test proves epoch-1 interruption can roll back without deleting,
  truncating, or overwriting the original ledger;
- unresolved intents still stop automatically and require a later human
  disposition;
- attempts to start seed 2 or 3 early fail before any model/data construction;
- mutated, missing, wrong-freeze, noncanonical, or swapped decision artifacts
  fail before run-root mutation;
- the complete project and fresh offline suites pass with warnings treated as
  errors;
- the exact-device launch preflight passes without model/dataset construction;
- machine-readable scope evidence records zero CIFAR operations, zero new
  optimizer diagnostics, and formal optimizer steps 0;
- the original tag
  `formal-freeze-densenet-bc100-12-cifar10plus-2026-08-23` is never moved or
  deleted;
- a separate human completion decision approves all new identities before a
  superseding freeze tag is created.

## Continuing prohibitions

Until both corrective assembly and its later completion package are approved,
the current source may not be modified. Throughout corrective assembly, Phase 6
entry, CIFAR model forward/loss/backward/optimizer/training/test evaluation,
prediction/argmax, accuracy/error, aggregation, pretrained results, and formal
optimizer steps remain forbidden. Formal optimizer steps remain **0**.

## Exact human authorization

**「我批准 formal-freeze corrective assembly decision package v1：接受 Phase 6 entry readiness audit 所列 H-013、H-014、H-015 三項 BLOCKER；批准僅在 static/mock/generated-only 範圍修正 frozen runner，包括可稽核的 epoch-1 initial-boundary rollback、正式三個 seed 的強制依序執行，以及 Phase 5 completion／Phase 6 entry 兩份 canonical decision artifacts 的逐位元 SHA256 launch verification；批准重建受影響的 project wheel、offline evidence、freeze-source/freeze-record、manifest 與 machine report 候選。原 annotated tag `formal-freeze-densenet-bc100-12-cifar10plus-2026-08-23` 必須保留且不得移動或刪除。仍禁止 Phase 6 entry、任何 CIFAR model forward/loss/backward/optimizer/training/test evaluation/prediction/accuracy/result aggregation、pretrained results 與正式 optimizer step；formal optimizer steps 維持 0。修正完成後必須另行批准 corrective freeze completion package，正式訓練仍須再另行批准 Phase 6 entry package。」**
