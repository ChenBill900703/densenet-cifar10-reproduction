# Phase 2 CIFAR-10 Validation Record

Date: **2026-08-16**

Disposition: **TECHNICALLY VALIDATED 2026-08-16 / COMPLETION APPROVED 2026-08-23 / NOT PHASE 5 FROZEN**

## Scope and authority

The human approved Phase 2 entry decision package v1 verbatim. Commit `c0b5331` records that authority before any dataset access. The work remained data-only: no model was used by the real-data diagnostics, no optimizer or scheduler was constructed, no loss or accuracy was computed, no pretrained result was downloaded, and optimizer steps remain zero.

## Audit chronology

| Commit/evidence | Meaning |
|---|---|
| `448328e` | Fail-closed archive preparation, exact binary decoder, official transforms, unapproved deterministic H-003 candidate, and synthetic tests committed before the complete artifacts were opened. |
| `7c9d28a` | Exact Toronto archive byte lengths, official MD5 matches, and locally computed SHA256 values committed before tar/pickle inspection. |
| `b2cd18b` | The first metadata comparison stopped on a terminal blank-line difference; the verifier was corrected to preserve and report that difference without weakening image/label equality. |
| `5409943` | Full 60,000-record artifact equivalence evidence committed. |
| `evidence/phase2_data_pipeline_diagnostic_2026-08-16.json` | Full candidate train epoch with zero/two workers plus complete normalization-only test pass, generated from clean commit `5409943`. |

## Artifact results

| Item | Verified result |
|---|---|
| Toronto Python archive | 170,498,071 bytes; MD5 `C58F30108F718F92721AF3B95E74349A`; SHA256 `6D958BE074577803D12ECDEFD02955F39262C83C16FE9348329D7FE0B5C001CE` |
| Toronto binary archive | 170,052,171 bytes; MD5 `C32A1D4AB5D03F1284B67883E8D87530`; SHA256 `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD` |
| Train canonical content | 50,000 records; exactly 5,000/class; SHA256 `A0181DA372C0D63A5920FDBEA2EC3F83ECBC552D378218E1CB473CF634941A3B` |
| Test canonical content | 10,000 records; exactly 1,000/class; SHA256 `8E2EB146AE340B09E24670F29CABC6326DBA54DA8789DAB6768ACF480273F65B` |
| Cross-format comparison | Every one of 60,000 labels and 184,320,000 pixel bytes is identical after canonical layout. |
| Metadata difference | Same ten ordered class names; binary `batches.meta.txt` contains one terminal blank line absent from Python metadata. Raw metadata is therefore not byte-identical. |
| Historical DenseNet Torch7 archive | Official-code URL returned HTTP 403; exact bytes/hash/equivalence remain `UNKNOWN`. No third-party replacement was used. |

The six safely materialized binary batches are exactly 30,730,000 bytes each. Their SHA256 values equal the corresponding canonical per-batch hashes in the artifact report. Derived files are ignored and reproducible from the locked binary archive; they are not the formal input artifact.

## Transform and decode results

The tests independently enforce:

- uint8 CHW RGB and row-major plane decoding;
- zero-based PyTorch targets corresponding to Torch7's one-based translated targets;
- raw 0-255 FP32 normalization with the official rounded constants;
- exact `Normalize -> HorizontalFlip -> zero-pad -> crop` order;
- padding after normalization, with normalized-zero border values;
- x/width and y/height axis semantics and inclusive crop offset 8;
- normalization-only test preprocessing;
- rejection of digest mismatch, duplicate/missing/unsafe members, symlinks, same-size content corruption, invalid labels, and ambient train augmentation RNG.

## Complete-epoch replay result

The data-only diagnostic used project seed `1021082110`, candidate epoch 1, physical batch 64, and the preregistered H-003 candidate stream domain `densenet-cifar10-loader-v1`.

| Result | Zero workers | Two workers |
|---|---:|---:|
| Samples | 50,000 | 50,000 |
| Batches | 782 | 782 |
| Final batch | 16 | 16 |
| Ordered targets SHA256 | `65D4E969F1E7C1ECD6E79CAF0E675C6999F02BF4DBC00F2B76801AB3B07DF666` | same |
| Transformed FP32 images SHA256 | `4354F39587A47A1DD3120AFCA8002CD3505F8A7BBCA56A1750A8F00485F74965` | same |

The explicit request/decision stream SHA256 is `B60C8F6D6B720736AEF84EA963F4D78CD2693D421283BAEBB8BDB9BD1756E4DD`. Worker-count replay is bit-exact. This validation did not itself approve H-003; the later human decision D-010 approved it on 2026-08-23.

The complete normalization-only 10,000-example diagnostic used 157 batches with a final batch of 16. Its transformed-image SHA256 is `657DD8A0FD8AECCD00213EB1044EBEB8EAC720CE9894976542F7139B0FF3252C`; target SHA256 is `F244313CD7CF97CD0712D5531B18E0CF6C2DC5444ABB018A459118F5D6714993`. No predictions or accuracy were computed.

## Test status

The combined suite contains **61 tests**: the preserved 47 Phase 1 tests plus 14 Phase 2 tests. The real-data evidence tests rerun the full cross-format comparison and the full zero/two-worker epoch rather than trusting the stored booleans.

## Completion disposition

Technical Phase 2 obligations passed before the human decision. On 2026-08-23, D-010 approved A-007/H-001/M-001 (canonical archive), H-003 (RNG/worker mapping), M-002 (evaluation loader), and M-003 (rounded constants) exactly as preregistered in `phase2_completion_decision_proposal.md`. Phase 2 is complete.

No Phase 3 authority, optimizer authority, formal training authority, accuracy result, or Phase 5 freeze follows from this validation or completion decision.
