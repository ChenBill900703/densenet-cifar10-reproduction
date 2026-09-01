from __future__ import annotations

import io
from pathlib import Path
import tarfile

from scripts import phase2_verify_cifar10_artifacts as verifier


def test_binary_metadata_preserves_names_and_reports_terminal_blank_line(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "metadata.tar"
    payload = ("\n".join(verifier.CLASS_NAMES) + "\n\n").encode("ascii")
    with tarfile.open(archive_path, "w") as archive:
        member = tarfile.TarInfo("cifar-10-batches-bin/batches.meta.txt")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    with tarfile.open(archive_path, "r") as archive:
        names, terminal_blank_lines = verifier._binary_class_names(archive)
    assert names == verifier.CLASS_NAMES
    assert terminal_blank_lines == 1
