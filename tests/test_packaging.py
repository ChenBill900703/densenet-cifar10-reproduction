from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _normalize_distribution(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def test_installed_package_imports_in_an_isolated_external_process(tmp_path: Path) -> None:
    program = """
import importlib.metadata
import json
import pathlib
import densenet_reproduction
import torch
print(json.dumps({
    "module": str(pathlib.Path(densenet_reproduction.__file__).resolve()),
    "project_version": importlib.metadata.version("densenet-reproduction"),
    "requirements": importlib.metadata.requires("densenet-reproduction"),
    "torch": torch.__version__,
}))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", program],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    report = json.loads(completed.stdout)
    module_path = Path(report["module"]).resolve()
    package_mode = os.environ.get("DENSENET_PACKAGE_MODE", "checkout-editable")
    if package_mode == "checkout-editable":
        assert module_path == (
            PROJECT_ROOT / "src" / "densenet_reproduction" / "__init__.py"
        ).resolve()
    elif package_mode == "formal-wheel":
        site_packages = (Path(sys.prefix) / "Lib" / "site-packages").resolve()
        assert module_path.is_relative_to(site_packages)
        assert not module_path.is_relative_to((PROJECT_ROOT / "src").resolve())
        direct_url = site_packages / "densenet_reproduction-0.1.0.dist-info" / "direct_url.json"
        assert not direct_url.exists()
    else:
        raise AssertionError(f"Unknown DENSENET_PACKAGE_MODE: {package_mode}")
    assert report["project_version"] == "0.1.0"
    assert report["requirements"] == ["torch==2.12.1"]
    assert report["torch"] == "2.12.1+cu130"


def test_environment_lock_exactly_matches_installed_third_party_distributions() -> None:
    lock_path = PROJECT_ROOT / "requirements" / "environment-lock.txt"
    locked = {
        _normalize_distribution(name): version
        for line in lock_path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
        for name, version in [line.split("==", 1)]
    }
    installed = {
        _normalize_distribution(distribution.metadata["Name"]): distribution.version
        for distribution in importlib.metadata.distributions()
        if _normalize_distribution(distribution.metadata["Name"])
        != "densenet-reproduction"
    }
    assert installed == locked


def test_requirement_files_pin_their_intended_indexes() -> None:
    requirements = PROJECT_ROOT / "requirements"
    assert (requirements / "bootstrap.txt").read_text(encoding="utf-8").splitlines()[
        0
    ] == "--index-url https://pypi.org/simple"
    assert (requirements / "runtime-dependencies.txt").read_text(
        encoding="utf-8"
    ).splitlines()[0] == "--index-url https://pypi.org/simple"
    assert (requirements / "runtime.txt").read_text(encoding="utf-8").splitlines()[
        0
    ] == "--index-url https://download.pytorch.org/whl/cu130"
    assert (requirements / "test.txt").read_text(encoding="utf-8").splitlines()[
        0
    ] == "--index-url https://pypi.org/simple"
