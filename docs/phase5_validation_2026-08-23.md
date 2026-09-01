# Phase 5 Freeze-Assembly Technical Validation

Status: **TECHNICALLY VALIDATED AND ACCEPTED BY D-020 / PHASE 5 FORMALLY FROZEN**

Date: **2026-08-23**

This record is `DERIVED` evidence for a freeze candidate. It is not a
`FORMAL-REPRODUCTION-RESULT`, does not create a freeze, and does not authorize
Phase 6 or a formal optimizer step.

## Candidate identities

| Item | Identity |
|---|---|
| Freeze-source commit | `5d5d6d89cde00134776a59924896758f30816281` |
| Canonical config | `C5F1B2DA0B2E0A5476531C0460313849EEB4058400BED0E0EFC3227D82A83213` |
| Freeze manifest candidate | `2EF356BF70F9C89C73E03D86D0726F0DA736D73A2FC6B7CC9255DFC1557E3DD1` |
| Project wheel | `0BA17933A23E0B8EB456FBBA87895F0A84F89E7B4B08CEC7A6B828E09F87C5F5` |
| Complete Git bundle | `B75036F025DD22A91503ABDA0252B846116C4A7A0E20CD5F60FC4B2C8E6D0357` |
| Third-party wheelhouse manifest | `DE3372B4E3AF16716623B527ADEC580DBEBFBD405E7E43ABB4C91450387C0BEF` |
| Python runtime archive | `BAC14B77461752024EBF95A820B1791F2061FD2B5B368E4D3BAD9A307460716F` |
| Python runtime manifest | `483F2926A83D533E5EAAADAECF2D1FA2BDCCAB00E50944D9CF3BAB1052137A2F` |
| Installed environment manifest | `47E7B175F4E802212DD8691358F678F1718BC0EABCCF08F499EB70F66F867136` |
| Offline hash requirements | `D19C719FDC77308502F55537F1587CEFCC393FD18EB5217D9CA171F1C46323F6` |
| Approved CIFAR archive | `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD` |

The freeze manifest deliberately leaves `freeze_record_commit` null. The
commit containing this evidence supplies that non-circular record identity and
will be named in the separate completion proposal.

## Supply-chain and reconstruction result

- 20 exact third-party wheels total 1,969,498,763 bytes; every filename,
  distribution/version, byte count, SHA256, and approved index origin is
  recorded.
- The project wheel was built twice with source commit timestamp
  `SOURCE_DATE_EPOCH`; both outputs were byte-identical. It contains the formal
  CLI entry point and all training/evaluation/checkpoint/launch modules.
- The Python archive freezes 8,264 non-cache runtime files. Mutable generated
  bytecode caches are intentionally excluded and ignored by live verification.
- A fresh environment was created from the extracted runtime with
  `--no-index --require-hashes`; it installed exactly 20 third-party
  distributions plus one non-editable project wheel.
- The resulting 21-distribution, 23,822-RECORD-file manifest was recomputed
  against the live environment after testing.
- The final freeze verifier passed 20/20 wheels, 8,264/8,264 runtime files,
  project-wheel CLI contents, all manifest-bound artifacts, and the complete
  Git bundle.

## Program and launch validation

The project venv and fresh offline formal-wheel environment each passed
156/156 under `-X dev -W error`. The external suite used only the checkout root
for evidence `scripts/`; `src/` was not injected. An isolated subprocess proved
the package came from the offline venv's `site-packages` and had no editable
`direct_url.json`.

Exact launch preflight then passed in that environment with Windows
`10.0.26100`, Python `3.12.13` build dated 2026-08-07, driver `591.86`, RTX 3070
Ti UUID `GPU-9f68fb0f-9bd0-a95c-d16e-8362b9d59e2e`, capability 8.6,
deterministic algorithms, cuDNN deterministic/benchmark-off, IEEE convolution
and matmul, and AMP/compile off. It constructed no model or dataset.

## Storage gate

The schema-faithful fixture contains model/BN state plus all 299 representative
momentum buffers and calls no optimizer. Its size is 6,633,987 bytes. Retaining
900 checkpoints requires 5,970,588,300 bytes; the approved 20% gate is
7,164,705,960 bytes. The final recorded free space was 50,998,046,720 bytes, so
the derived gate passed. Actual checkpoints may differ modestly in serialized
content compression; the runner rechecks the frozen byte gate before launch
and never deletes earlier evidence automatically.

## Scope ledger

Phase 5 assembly performed zero CIFAR model forwards, losses, backwards,
optimizer calls, predictions, argmax operations, result aggregations, or test
record accesses. No new Phase 5 optimizer diagnostic exists. The complete
regression suite still contains the previously approved Phase 3/4 generated-
only mechanics tests; those are not Phase 5 or formal calls. Formal optimizer
steps remain exactly **0**.

## Residual limitations

- Authors' seeds, private dependency binaries, machine, and exact reduction
  trajectory remain `UNKNOWN`.
- The frozen candidate is a human-approved semantic PyTorch port, not a claim
  of historical bitwise equivalence.
- Large wheel/runtime/source artifacts remain in the ignored local artifact
  root and are hash-bound by tracked manifests. The root repository still has
  no off-machine remote; a Git bundle is portable evidence, not an offsite
  backup.
- D-020 later approved the Phase 5 completion tuple and created the preserved
  first formal tag. A subsequent pre-execution Phase 6 readiness audit found
  H-013 through H-015; therefore no Phase 6 authorization, CIFAR training,
  evaluation, or formal result exists.
