# Phase 6 Preflight/ACL Corrective Assembly Technical Validation

Status: **TECHNICALLY VALIDATED / CORRECTIVE-FREEZE COMPLETION DECISION PENDING / PHASE 6 EXECUTION FORBIDDEN**

Date: **2026-08-24**

This record is `DERIVED` evidence under D-030 and D-032. It is not a
`FORMAL-REPRODUCTION-RESULT`, does not create a formal tag, and does not
authorize Phase 6 re-entry, training, evaluation, aggregation, or an optimizer
call.

## Candidate identities

| Item | Identity |
|---|---|
| Corrective freeze-source commit | `47028a6b4ab38b007e59ce763cc01d21824abad0` |
| Schema-v2 freeze manifest candidate | SHA256 `15CB6FD32E5D15D33F1EAF1F716938BC80A73C1E1466E3AA44108E5E08FFDAC1` |
| Project wheel | 57,916 bytes; SHA256 `DECE8F41A0ACDDAC6869F38A3C9FE147196C799150544870CE59FB426BB7904D` |
| Installed environment manifest | SHA256 `00B4D3295826F22617FCF438F6C1E344E95686729BE7F82B6F5B0C4D440CF0B0` |
| Offline requirements | SHA256 `DF0737C86147DE251D1D8CCC4A09CD7D748464BD17FD952C2F672EB8D2F9A362` |
| Complete Git bundle | 4,145,187 bytes; SHA256 `17F99A1E451A3959DD4C63159D1945E52CFA9CE4C1C16AE5569DF1BE03CFCAF3` |
| Machine report | SHA256 `96304D146FD3BC1FBD9A5B039140A9D373868367C9F55345E74D169F30E0CAE7` |

The later commit containing this validation and the candidate evidence is the
non-circular freeze-record identity. The manifest deliberately keeps
`freeze_record_commit` null.

## D-032 helper recovery

The `.git` before/after manifests prove that one explicit, non-inheriting
`WRITE_DAC/ChangePermissions` ACE was added for
`<REDACTED_EXECUTION_ACCOUNT>`. Owner, inheritance protection, all non-target ACEs,
Git objects, index, tracked bytes, HEAD, and clean state were unchanged. The
Codex owner-context helper then resumed as
`<REDACTED_SANDBOX_ACCOUNT>`.

## H-016/H-017/H-018 correction

- Prepared-directory before/failure/after snapshots retain all seven file
  sizes and SHA256 values exactly.
- The only effective access delta is the approved account's
  RX/read/traverse/synchronize rule on the protected root, inherited by the
  seven approved files.
- The first `icacls /T` attempt stopped after detecting an unexpected root
  inheritance drift. That state is preserved; protection and non-target ACE
  semantics were restored before validation completed.
- The committed script no longer invokes `icacls.exe`; it applies one root
  rule through `Set-Acl`, preserves owner/protection, and compares ACE semantic
  sets independent of display order.
- Account/SID and the five training batches are verified before formal-root,
  seed-directory, model, optimizer, dataset, or loader mutation.
- Training split verification does not stat/open/hash/map/decode
  `test_batch.bin`; evaluation test access remains after the all-training gate.

## Rebuild and verification

- Two source-date-epoch project-wheel builds were byte-identical.
- The complete Git bundle verifies all history and refs.
- The unchanged 20-wheel wheelhouse and 8,264-file Python runtime were reused
  only after exact verification.
- A fresh environment was reconstructed with `--no-index --require-hashes`.
  It contains 21 distributions and 23,822 installed RECORD files.
- The installed manifest was bit-exact before and after testing.
- Project and fresh offline formal-wheel environments each passed **175/175**
  with development warnings treated as errors.
- Source verification passed 19/19 files and 5/5 complete repositories.
- The exact `<REDACTED_EXECUTION_ACCOUNT>` Phase 2 replay passed with training
  workers 0/2 bit-exact, no model/optimizer, zero optimizer steps, and no
  accuracy computation.
- Schema-v2 freeze verification passed 20/20 wheels, 8,264/8,264 runtime
  files, project wheel, bundle, config, dataset, paper, and source lock in both
  project and fresh environments.
- Exact live preflight passed for the frozen account/SID, Windows/Python,
  driver, RTX 3070 Ti UUID/capability, deterministic IEEE-FP32, AMP off, and
  compile off, without model, dataset, optimizer, or formal-root construction.
- Storage gate passed: 7,164,705,960 required bytes versus 44,484,419,584
  observed free bytes.

## Preserved state and remaining gates

The original formal tags still peel to `4e69d397f7935ea2f4f9eedc83ecf43547946626`
and `74266d3904a446ac7d41ee1e4fe4f79016877026`; neither moved. D-028
still contains exactly two zero-byte SHA256-empty files and remains abandoned.

Formal optimizer calls remain exactly **0**. A separate human-approved
corrective-freeze completion package is required before the proposed
superseding tag may be created. A further, newly manifest-bound Phase 6 entry
approval is required before any formal execution.
