"""Verify and safely prepare the locked Toronto CIFAR-10 binary archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from densenet_reproduction import prepare_cifar10_binary_archive


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = PROJECT_ROOT / "evidence" / "cifar10-artifacts.json"
DEFAULT_ARCHIVE = PROJECT_ROOT / "data" / "raw" / "cifar-10-binary.tar.gz"
DEFAULT_DESTINATION = PROJECT_ROOT / "data" / "prepared"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args()

    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    record = lock["artifacts"]["toronto_binary"]
    prepared = prepare_cifar10_binary_archive(
        args.archive,
        args.destination,
        expected_md5=record["md5"],
        expected_sha256=record["sha256"],
    )
    manifest = json.loads(
        (prepared / "prepared-manifest.json").read_text(encoding="utf-8")
    )
    print(
        json.dumps(
            {
                "classification": "PHASE2-PREPARED-CACHE-NOT-FORMAL-FREEZE",
                "prepared": str(prepared.resolve()),
                "manifest": manifest,
                "optimizer_constructed": False,
                "optimizer_steps": 0,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
