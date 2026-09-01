# Formal-Freeze Corrective Assembly Technical Validation

Status: **TECHNICALLY VALIDATED / CORRECTIVE-FREEZE COMPLETION DECISION PENDING / PHASE 6 FORBIDDEN**

Date: **2026-08-24**

This record is `DERIVED` evidence for the D-022 corrective freeze candidate,
accepted and frozen by D-024 on 2026-08-24.
It is not a `FORMAL-REPRODUCTION-RESULT`, does not create a new freeze, and
does not authorize Phase 6 or a formal optimizer step.

## Corrective identities

| Item | Identity |
|---|---|
| Corrective freeze-source commit | `9efdd584f664df3b9f74ac9917e3b389400d61ec` |
| Corrective manifest candidate | SHA256 `64CFB2826BFE6D77CB9EE15E0BEF544186D51947C843A96C7C9F2DD9D82CABC7` |
| Corrected project wheel | 55,930 bytes; SHA256 `E740FD93A0F9356F5BFCCD4C18AE67FD0D6811DD2CDF720AD78BFBE069A84338` |
| Installed environment manifest | SHA256 `3DCBA6F2883C6C7E08C1BEF7AB03B73C5D7E3A3C0FE9539F479AEE51AEC8DA72` |
| Offline requirements | SHA256 `89A6106E8B201DB52265977B52F8559A99129FEEF5007813A120F55E2933BA50` |
| Complete Git bundle | 2,822,097 bytes; SHA256 `55C605DD3461FB238681356EAFFFFEAE8AD08487DA8F27A5AD321BAC4753F10D` |
| Machine report | SHA256 `02A173DFBBA76470AE401438841871528C203BB76B7CC7D76DBDF853FACB8F87` |

The later commit containing this evidence is the non-circular corrective
freeze-record identity. It will be named in the separate completion proposal.

## H-013 validation

- The explicit initial-boundary mode is mutually exclusive with checkpoint
  resume.
- It reopens rather than replaces the fixed seed directory.
- It validates the complete canonical append-only ledger and training-progress
  log, preserves earlier completed physical calls, and rejects another seed,
  a torn/noncanonical/inconsistent progress record, any checkpoint artifact,
  or any unresolved optimizer intent.
- A mock-only path proved that all initial-boundary guards pass before the mock
  model factory is reached. An unresolved intent and a pre-existing checkpoint
  both fail before model or data construction.

## H-014 validation

- New and resumed training paths enforce seed order
  `1021082110`, `1747066946`, `869460408`.
- Every earlier seed must retain all 300 checkpoint bytes/manifests with exact
  epoch, accepted-step, freeze, ledger-head, and physical-call provenance.
- Any later seed directory or premature final-test evidence fails closed.
- The public CLI and the lower training API both apply the order guard before
  model or dataset construction.

## H-015 validation

- Raw authorization JSON is not a runtime capability.
- The Phase 5-completion and Phase 6-entry decision files must be distinct,
  canonical closed-schema records, approved at formal step zero, bind the same
  manifest, and match the authorization's exact SHA256 values.
- Missing, swapped, noncanonical, unapproved, wrong-freeze, and wrong-hash
  artifacts fail before formal-root mutation.
- Every formal training, evaluation, aggregation, and optimizer-call adapter
  still requires the process-local verified capability.

## Rebuild and verification result

- Two independent source-date-epoch wheel builds were byte-identical.
- The existing 20 third-party wheels and 8,264-file Python runtime remained
  unchanged and reverified exactly.
- A fresh environment was rebuilt offline with `--no-index --require-hashes`.
  It contains 21 distributions and 23,822 installed RECORD files; the project
  package is the non-editable corrected wheel in `site-packages`.
- The project environment and fresh offline formal-wheel environment each
  passed **166/166** with development warnings treated as errors.
- The source verifier passed 19/19 files and 5/5 complete repositories.
- The corrected manifest verifier passed 20/20 wheels, 8,264/8,264 runtime
  files, the corrected project wheel, and the complete Git bundle.
- Exact-device launch preflight passed on the same Windows/Python/driver/RTX
  3070 Ti UUID/compute capability/deterministic IEEE-FP32 identity without
  model or dataset construction.
- The storage gate passed: 7,164,705,960 required bytes versus
  47,745,703,936 observed free bytes.

## Preserved scientific identity

The canonical config SHA256 remains
`C5F1B2DA0B2E0A5476531C0460313849EEB4058400BED0E0EFC3227D82A83213`;
the CIFAR archive remains
`C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD`;
the Python runtime remains
`BAC14B77461752024EBF95A820B1791F2061FD2B5B368E4D3BAD9A307460716F`.
No model, loss, optimizer, LR, RNG, data, seed, evaluation, result, precision,
or batch-size policy changed.

The first annotated tag
`formal-freeze-densenet-bc100-12-cifar10plus-2026-08-23` still points to
`4e69d397f7935ea2f4f9eedc83ecf43547946626` and was not moved or deleted.

## Scope ledger

The corrective work performed zero CIFAR model forwards, losses, backwards,
optimizer calls, predictions, accuracy operations, test evaluations, or
aggregations and introduced no optimizer diagnostic. The complete regression
suite still includes previously approved generated-only mechanics tests. Formal
optimizer steps remain exactly **0**.

## Remaining gates and limitations

- The human approved the corrective-freeze completion package as D-024 on
  2026-08-24; the corrected baseline is frozen.
- Phase 6 entry and formal execution still require another separate approval.
- The root repository still has no off-machine remote. Large artifacts remain
  in the ignored local artifact root and are hash-bound by tracked manifests;
  the complete Git bundle is portable evidence, not an offsite backup.
