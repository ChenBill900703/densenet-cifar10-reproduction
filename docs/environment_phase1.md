# Phase 1 environment record

## Classification and scope

- Record date: **2026-08-16 Asia/Taipei**.
- Classification: environment observation for Phase 1; **not a formal reproduction result**.
- Formal optimizer steps: **0**.
- Purpose: make the architecture tests locally repeatable before dataset and training phases exist.

## Project location and virtual environment

| Field | Observed value |
|---|---|
| Project root | `D:\DenseNet — Densely Connected Convolutional Networks` |
| Virtual environment | `D:\DenseNet — Densely Connected Convolutional Networks\.venv` |
| Prompt | `densenet-repro` |
| Host OS observed by Python | Windows 11, build 26100, AMD64 |
| Python | CPython 3.12.13, 64-bit, MSC v.1944 |
| `include-system-site-packages` | `false` |
| Base interpreter used on this host | `<REDACTED_USER_HOME>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` |

The base-interpreter path is host-specific and is not a portability requirement. A fresh 64-bit CPython 3.12 environment can be reconstructed with the commands in the root README.

## Direct dependency decisions

| Package | Exact version | Source/purpose |
|---|---|---|
| PyTorch | `2.12.1+cu130` | Official PyTorch CUDA 13.0 wheel index; modern-framework port runtime |
| TorchVision | `0.27.1+cu130` | Pinned now for a later gated data phase; no TorchVision model is used |
| pytest | `9.0.2` | Phase 1 verification only |
| setuptools | `78.1.0` | Exact local editable-build backend |
| pip | `25.0.1` | Environment bootstrap snapshot |

The complete transitive snapshot is `requirements/environment-lock.txt`, and the README applies it as a constraint to every third-party dependency installation step. The authoritative fresh-install sequence separates `bootstrap.txt`, `runtime-dependencies.txt`, `runtime.txt`, and `test.txt`: ordinary dependencies come from PyPI, while PyTorch/TorchVision are installed with `--no-deps` from the official PyTorch CUDA index. The editable project install itself is local, uses `--no-deps --no-build-isolation`, and is therefore not a third-party dependency resolution step. The project metadata separately declares its actual import dependency `torch==2.12.1`; the `+cu130` wheel identity remains exact in `runtime.txt` and the environment lock.

This Phase 1 lock pins resolved versions but does **not** yet contain wheel artifact SHA256 values. It therefore prevents ordinary version drift but is not a bit-for-bit supply-chain freeze. Phase 5 must either add verified artifact hashes (and retain the installers) or record an equivalently immutable package source before any formal run.

## GPU observation

| Field | Observed value |
|---|---|
| GPU | NVIDIA GeForce RTX 3070 Ti |
| GPU UUID | `GPU-9f68fb0f-9bd0-a95c-d16e-8362b9d59e2e` |
| VRAM | 8192 MiB |
| Compute capability | 8.6 |
| Driver | 591.86 |
| PyTorch CUDA runtime | 13.0 |
| `torch.cuda.is_available()` | `True` |

This is a capability observation, not the later frozen training environment. Driver, Windows build, library algorithms, determinism settings, and the complete hardware/software lock still require Phase 4/5 capture before formal training.

## Verification commands

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\phase1_gpu_smoke.py
.\.venv\Scripts\python.exe scripts\phase1_precision_diagnostic.py
.\.venv\Scripts\python.exe scripts\phase1_determinism_diagnostic.py
```

All four verification/diagnostic commands above use generated tensors only. None creates an optimizer, downloads pretrained results, reads CIFAR, measures accuracy, or takes an optimizer step.

The final four-file dependency sequence and editable install were exercised in a brand-new project-external virtual environment on 2026-08-16 after the complete audit suite was assembled. `pip check`, isolated installed-package import, syntax compilation, and all 47 tests passed there. This proves the documented sequence reconstructed the observed Phase 1 software environment on this host; it does not supply the missing wheel artifact hashes required for a later supply-chain freeze.
