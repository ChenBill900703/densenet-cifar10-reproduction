"""Paired CPU/CUDA precision diagnostic for the Phase 1 graph.

This script uses generated tensors, constructs no optimizer, performs no
training step, and reports observations rather than adopting a formal precision
or determinism policy.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import sys

import torch

from densenet_reproduction import build_formal_model, state_dict_sha256


MODEL_TEST_SEED = 28_000
INPUT_TEST_SEED = 28_001


def _raw_tensor_sha256(tensor: torch.Tensor) -> str:
    contiguous = tensor.detach().cpu().contiguous()
    raw = bytes(contiguous.reshape(-1).view(torch.uint8).tolist())
    return hashlib.sha256(raw).hexdigest().upper()


def _relative_infinity_error(
    observed: torch.Tensor, reference: torch.Tensor
) -> dict[str, float | int]:
    difference = (observed - reference).abs()
    numerator = float(difference.max().item())
    reference_max = float(reference.abs().max().item())
    denominator = max(reference_max, 1.0)
    return {
        "elements": observed.numel(),
        "max_absolute_error": numerator,
        "reference_max_absolute_value": reference_max,
        "denominator_floor": 1.0,
        "denominator_used": denominator,
        "relative_infinity_error": numerator / denominator,
    }


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; no precision diagnostic was executed.")

    device = torch.device("cuda:0")
    properties = torch.cuda.get_device_properties(device)
    model = build_formal_model(test_seed=MODEL_TEST_SEED).eval()
    initial_state_hash = state_dict_sha256(model)
    inputs_cpu = torch.randn(
        3,
        3,
        32,
        32,
        generator=torch.Generator().manual_seed(INPUT_TEST_SEED),
    )
    with torch.inference_mode():
        cpu_logits = model(inputs_cpu)

    model.to(device)
    inputs_cuda = inputs_cpu.to(device)
    original_cudnn_precision = torch.backends.cudnn.conv.fp32_precision
    original_matmul_precision = torch.backends.cuda.matmul.fp32_precision
    try:
        torch.backends.cuda.matmul.fp32_precision = "ieee"
        torch.backends.cudnn.conv.fp32_precision = "tf32"
        with torch.inference_mode():
            tf32_logits = model(inputs_cuda).cpu()
        torch.cuda.synchronize(device)

        torch.backends.cudnn.conv.fp32_precision = "ieee"
        with torch.inference_mode():
            ieee_logits = model(inputs_cuda).cpu()
        torch.cuda.synchronize(device)
    finally:
        torch.backends.cudnn.conv.fp32_precision = original_cudnn_precision
        torch.backends.cuda.matmul.fp32_precision = original_matmul_precision

    outputs = {
        "cpu": cpu_logits,
        "cuda_tf32_convolution": tf32_logits,
        "cuda_ieee_convolution": ieee_logits,
    }
    if not all(torch.isfinite(output).all().item() for output in outputs.values()):
        raise RuntimeError("A non-finite logit was observed in the precision diagnostic.")

    report = {
        "classification": "PHASE1-PRECISION-DIAGNOSTIC-ONLY",
        "evidence_class": "DERIVED",
        "record_date": datetime.now().astimezone().date().isoformat(),
        "optimizer_constructed": False,
        "optimizer_steps": 0,
        "model_test_seed": MODEL_TEST_SEED,
        "input_test_seed": INPUT_TEST_SEED,
        "input_shape": list(inputs_cpu.shape),
        "logit_elements_per_output": cpu_logits.numel(),
        "initial_state_sha256": initial_state_hash,
        "torch": torch.__version__,
        "torch_cuda_runtime": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "device": torch.cuda.get_device_name(device),
        "compute_capability": f"{properties.major}.{properties.minor}",
        "python": sys.version,
        "observed_process_defaults": {
            "cudnn_convolution_fp32_precision": original_cudnn_precision,
            "matmul_fp32_precision": original_matmul_precision,
            "deterministic_algorithms": (
                torch.are_deterministic_algorithms_enabled()
            ),
            "cudnn_enabled": torch.backends.cudnn.enabled,
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "cudnn_deterministic": torch.backends.cudnn.deterministic,
        },
        "diagnostic_matmul_fp32_precision": "ieee",
        "output_raw_sha256": {
            name: _raw_tensor_sha256(output) for name, output in outputs.items()
        },
        "comparisons": {
            "cuda_tf32_vs_cpu": _relative_infinity_error(tf32_logits, cpu_logits),
            "cuda_ieee_vs_cpu": _relative_infinity_error(ieee_logits, cpu_logits),
            "cuda_tf32_vs_cuda_ieee": _relative_infinity_error(
                tf32_logits, ieee_logits
            ),
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
