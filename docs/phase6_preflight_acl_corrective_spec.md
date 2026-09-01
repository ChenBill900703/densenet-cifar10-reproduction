# Phase 6 Preflight/ACL Corrective Specification

Status: **D-030 AUTHORIZED / SOURCE CANDIDATE UNDER VALIDATION / FORMAL EXECUTION FORBIDDEN**

Date: **2026-08-24**

Evidence classification: the observed H-016/H-017 control flow is `DERIVED`;
the split-scoped preflight, host account/SID, and ACL policy are
`IMPLEMENTATION-ASSUMPTION`. Nothing here is a
`FORMAL-REPRODUCTION-RESULT`.

## Scope

This specification implements only D-030. It does not change DenseNet
mathematics, CIFAR records, augmentation, normalization, RNG domains, project
seeds, batch size, precision, loss, SGD, LR, checkpoint, evaluation, or
aggregation rules. It authorizes no formal optimizer call.

## Closed execution identity

The new freeze-manifest candidate uses schema version 2 and adds these required
environment fields:

- account: `<REDACTED_EXECUTION_ACCOUNT>`;
- SID: `<REDACTED_EXECUTION_SID>`.

The live runner observes the SAM-compatible account independently of the token
SID and requires both to match exactly. A schema-v1 manifest remains readable
as historical evidence but is explicitly ineligible for execution by the
corrected runner.

## Split-scoped prepared verification

`verify_prepared_cifar10_split` safely resolves a non-symlink prepared
directory and `prepared-manifest.json`, verifies the closed manifest schema and
source-archive identity, and checks the complete six-name manifest inventory.
Physical file access is split-scoped:

- `train`: resolve, stat, open, and SHA256 only `data_batch_1.bin` through
  `data_batch_5.bin`;
- `test`: resolve, stat, open, and SHA256 only `test_batch.bin`.

The training verifier and `Cifar10BinaryDataset(split="train")` must succeed
when the manifest contains the locked test metadata but the physical
`test_batch.bin` is absent. This is the primary H-018 negative oracle. It proves
that training does not stat, resolve, open, map, hash, or decode test bytes.

## Formal train ordering

For the CLI `train` command, the required ordering is:

1. validate canonical config;
2. read authorization and enforce deterministic GPU policy;
3. load schema-v2 freeze manifest and verify live account/SID;
4. verify all frozen artifact/environment/GPU identities;
5. hash and validate D-024/D-025 canonical decision artifacts;
6. verify the prepared manifest and five training batches;
7. resolve and check formal-root storage;
8. only then create/reopen the manifest/seed directory;
9. only then enter the direct training adapter.

The direct training API independently repeats launch authorization and
split-scoped prepared verification before it resolves or mutates run state and
before device, model, optimizer, dataset, or loader construction. This prevents
a caller from bypassing the CLI guard.

## Formal evaluation ordering

Evaluation does not verify or access prepared test bytes in common CLI
preflight. The evaluation adapter must first verify all three immutable
300-epoch training runs and fixed evaluation order. Only after those gates pass
may it verify `test_batch.bin`. Test verification must still occur before a
final-test attempt/progress artifact or model/optimizer is constructed.

## ACL correction contract

`scripts/phase6_acl_corrective.ps1` is the only authorized ACL mutation path.
It must run as the existing target-directory owner and it:

- accepts only the approved directory leaf, account, and SID;
- rejects reparse points, extra/missing members, or a pre-existing target SID
  ACE;
- captures owner, inheritance protection, SDDL, normalized ACEs, file sizes,
  and file SHA256 values before the change;
- adds only `(OI)(CI)(RX)` to the approved SID for the target and its exact
  seven children;
- never takes ownership, resets ACLs, replaces inheritance, removes an ACE, or
  grants modify/write/delete/ownership/ACL-change rights;
- captures and validates the complete after state;
- requires every non-target ACE, owner, inheritance-protection value, file
  size, and SHA256 value to remain exact;
- records a failure snapshot if the ACL operation returns nonzero.

If the existing owner context is unavailable or any invariant fails, the
operation stops. Copying or re-extracting the dataset is not a workaround.

## Mandatory regression oracles

The corrective corpus proves:

- wrong account/SID stops before prepared access;
- missing, wrong-hash, or symlink-classified training members stop before
  formal-root storage/mutation;
- main CLI prepared failure cannot reach seed-directory creation or the
  training adapter;
- the train verifier and train dataset work with no physical test batch;
- incomplete training prevents any test prepared access;
- after the training gate, test verification occurs before attempt files and
  model construction;
- schema-v1 manifests cannot execute under the corrected runner;
- the ACL script contains the exact SID/RX grant and no takeover/reset/modify
  grant path;
- D-028 remains exactly two zero-byte SHA256-empty files;
- formal optimizer calls remain zero.

## Remaining lifecycle sequence

After source tests and real prepared-data/ACL evidence pass, rebuild the
project wheel twice, the offline installed environment, exact launch evidence,
Git bundle, schema-v2 freeze manifest, and machine report. Technical completion
still requires a separate human corrective-freeze completion approval. Only
that approval may authorize the proposed annotated tag, and a later distinct
Phase 6 entry approval must bind the new manifest before any formal execution.
