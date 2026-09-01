"""GPU-only synthetic Phase 1 check; this script never creates an optimizer."""

from __future__ import annotations

from contextlib import contextmanager
import json

import torch
from torch import nn

from densenet_reproduction import (
    build_formal_model,
    parameter_breakdown,
    state_dict_sha256,
)


TEST_ONLY_SEED = 20_260_816


@contextmanager
def _tf32_disabled_smoke_settings():
    """Disable TF32 for this diagnostic; this is not a determinism guarantee."""

    previous_matmul_tf32 = torch.backends.cuda.matmul.allow_tf32
    previous_cudnn_tf32 = torch.backends.cudnn.allow_tf32
    defaults = {
        "matmul_allow_tf32": previous_matmul_tf32,
        "cudnn_allow_tf32": previous_cudnn_tf32,
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "cudnn_deterministic": torch.backends.cudnn.deterministic,
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
    }
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    try:
        yield defaults
    finally:
        torch.backends.cuda.matmul.allow_tf32 = previous_matmul_tf32
        torch.backends.cudnn.allow_tf32 = previous_cudnn_tf32


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; no GPU smoke check was executed.")

    with _tf32_disabled_smoke_settings() as observed_process_defaults:
        device = torch.device("cuda:0")
        properties = torch.cuda.get_device_properties(device)
        model = build_formal_model(test_seed=TEST_ONLY_SEED)
        initial_state_hash = state_dict_sha256(model)
        parameters = parameter_breakdown(model)
        model.to(device).train()

        cpu_generator = torch.Generator().manual_seed(TEST_ONLY_SEED + 1)
        inputs = torch.randn(2, 3, 32, 32, generator=cpu_generator).to(device)
        targets = torch.tensor([0, 9], dtype=torch.long, device=device)
        torch.cuda.reset_peak_memory_stats(device)

        logits = model(inputs)
        loss = nn.functional.cross_entropy(logits, targets)
        loss.backward()
        torch.cuda.synchronize(device)

        missing_gradients = []
        nonfinite_gradients = []
        for name, parameter in model.named_parameters():
            if parameter.grad is None:
                missing_gradients.append(name)
            elif not torch.isfinite(parameter.grad).all().item():
                nonfinite_gradients.append(name)

        report = {
            "classification": "PHASE1-SYNTHETIC-SMOKE-ONLY",
            "optimizer_constructed": False,
            "optimizer_steps": 0,
            "torch": torch.__version__,
            "torch_cuda_runtime": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
            "device": properties.name,
            "compute_capability": f"{properties.major}.{properties.minor}",
            "total_device_memory_bytes": properties.total_memory,
            "peak_allocated_memory_bytes": torch.cuda.max_memory_allocated(device),
            "initial_state_sha256": initial_state_hash,
            "trainable_parameters": parameters["total"],
            "logits_shape": list(logits.shape),
            "loss_is_finite": bool(torch.isfinite(loss).item()),
            "missing_gradients": missing_gradients,
            "nonfinite_gradients": nonfinite_gradients,
            "observed_process_defaults": observed_process_defaults,
            "smoke_matmul_allow_tf32": torch.backends.cuda.matmul.allow_tf32,
            "smoke_cudnn_allow_tf32": torch.backends.cudnn.allow_tf32,
            "smoke_is_determinism_claim": False,
        }
    print(json.dumps(report, indent=2, sort_keys=True))

    if not report["loss_is_finite"] or missing_gradients or nonfinite_gradients:
        raise RuntimeError("The Phase 1 GPU synthetic check failed.")


if __name__ == "__main__":
    main()
