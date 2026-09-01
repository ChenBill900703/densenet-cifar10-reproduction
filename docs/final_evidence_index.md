# Final Evidence Index

Status date: **2026-08-28**

This index gives the shortest auditable path from primary evidence to the final numerical claim.

## Primary sources

| Evidence | Path / identity | SHA256 / commit | Class |
|---|---|---|---|
| User-supplied arXiv v5 paper | `docs/1608.06993v5.pdf` | `B55AA1ADBDF07F731DAA84B94D23103D1EB22D1821A556B80212DEBEE69B096D` | `PAPER-SPECIFIED` source |
| Author repository | `sources/DenseNet-official` | `6d4c8da6a1ef750c9116807b98e7c6265f51d762` | `OFFICIAL-CODE-SPECIFIED` source |
| Historical SGD | `sources/torch-optim` | `656c42af1f996e4a5d6aae3b9aeac831ca162241` | `HISTORICAL-DEPENDENCY-BACKED` source |
| Historical Torch nn | `sources/torch-nn` | `bae729acce1930aa46be5c6ca0d7272f7eba406e` | `HISTORICAL-DEPENDENCY-BACKED` source |
| Historical cudnn.torch | `sources/cudnn.torch` | `008c49de3982119378576fa4244e472a50fd9ebe` | `HISTORICAL-DEPENDENCY-BACKED` source |
| Complete source lock | `evidence/source-lock.json` | `AFC49C8CD4A7D11B3DC9CF19660B78AFF9C1833288A0AE555F688D62D1CC8354` | `DERIVED` |

## Frozen execution identity

| Evidence | Path / identity | SHA256 / commit |
|---|---|---|
| Corrective freeze manifest | `evidence/phase6_ledger_performance_corrective_manifest_candidate.json` | `6CC22F7D918DF1689C4E14A33E8BB4FDAF502EF51149AF1E6537D2618547EC26` |
| Frozen source | Git commit | `863375d4082abaa2a7f6580e4f90c3ec114cbce3` |
| Freeze record | Git commit | `0ac24e07f54342428b698297db689f1408ea0f43` |
| Canonical config | `config/formal_config.json` | `C5F1B2DA0B2E0A5476531C0460313849EEB4058400BED0E0EFC3227D82A83213` |
| CIFAR-10 archive | `data/raw/cifar-10-binary.tar.gz` | `C4A38C50A1BC5F3A1C5537F2155AB9D68F9F25EB1ED8D9DDDA3DB29A59BCA1DD` |
| Corrected wheel | formal offline artifact | `D31FE8A0DFBDBF4B4100C28E587DDDA98A13EE63219B373143DF41C01F8CE859` |
| Python runtime archive | formal offline artifact | `BAC14B77461752024EBF95A820B1791F2061FD2B5B368E4D3BAD9A307460716F` |
| Installed environment manifest | `evidence/phase6_ledger_performance_corrective_installed_environment_2026-08-24.json` | `1E0D0EA18AE43BCBEDA2962EB363C7D8CE7FBB8B2B03000D33A8BEA130A7C953` |
| Corrective machine report | `evidence/phase6_ledger_performance_corrective_machine_report_2026-08-24.json` | `5BA5972212E1A55BC1BEBC28CB9AEAA69CC7235F46ECB9B1D9F51B717C137286` |

## Training completion evidence

| Seed | Verification report | Report SHA256 | Calls / checkpoints |
|---:|---|---|---|
| 1021082110 | `evidence/phase6_seed1_completion_verification_2026-08-26.json` | `166B62BCA6C4960567E90B3FBB67FE4D7766A711642E097F6A0F10C5BD573F39` | 234,600 / 300 |
| 1747066946 | `evidence/phase6_seed2_completion_verification_2026-08-27.json` | `68D76433B70DB08B046E9BDDE774E0AAF6BA734AA4159AF0DEE16CD1047B1CE5` | 234,600 / 300 |
| 869460408 | `evidence/phase6_seed3_completion_verification_2026-08-28.json` | `394F9C859045F6E21488A7C6270CF3284CE17BE56B680FCBAA6EC9367160623B` | 234,600 / 300 |

All three reports record 234,600 intents, 234,600 completions, zero unresolved intents, 234,600 finite progress records, and 300 checkpoint/manifests.

## Final-test evidence

| Seed | Result | Result SHA256 | Verification report SHA256 |
|---:|---:|---|---|
| 1021082110 | 466/10,000 = 4.66% | `6D67DD39B18079347DAAD38413113A20D1B553132D33D96107C3561788F5DF92` | `555A56B8AD02C2E8C7DC9B3C3698C590C3BE5DB9C5D4C2F6B605BEBB7F54FB10` |
| 1747066946 | 461/10,000 = 4.61% | `7A42A217A2A30DF30B6C6BEE75DCFFF9629B77AD8588C4D915E2A72D8BCBF84C` | `AAD30CE615B1F80CB95E2F8E428191C7E4D88671FC7DBE7C70CC95E3D27D286F` |
| 869460408 | 481/10,000 = 4.81% | `D274D0B8BF5AE6E10803666EC022A66D3416F8EAE89F3138EF206506B3FC97B4` | `63866185C002F059C932A0960725806F858D67F894D4ABD7303BC54EBBC6B511` |

Each result has exactly one canonical attempt, 157 sequential test-progress records, and 10,000 test examples.

## Aggregate and final claim

| Evidence | Path | SHA256 |
|---|---|---|
| Aggregate result | `runs/formal/6CC22F7D918DF1689C4E14A33E8BB4FDAF502EF51149AF1E6537D2618547EC26/aggregate-result.json` | `A2669C814149C11101B9963B7FC6F24248EE80BAA674D8721628A80166F6D46A` |
| Aggregate verification | `evidence/phase6_aggregate_verification_2026-08-28.json` | `85921C4A779F8D1169AEF817FA8DC248E607D085B4578A0E9219CED65D773A9B` |

Frozen aggregate: ordered counts `[466,461,481]`; mean `352/75% = 4.693333333333%`; sample SD `0.104083299973` percentage points; selection `none`.

Paper comparison: Table 2 value 4.51%; reproduction mean difference `+0.183333333333` percentage points.

## Historical failures preserved outside the result

- D-028 contains two immutable zero-byte files from the pre-optimizer access failure.
- D-043 preserves the old incomplete/non-resumable namespace with exactly 24,421 physical calls.
- Neither namespace contributes a checkpoint, seed result, test attempt, or value to the final aggregate.

