"""Phase 2 CIFAR-10 artifact and deterministic data-pipeline primitives.

This module contains no optimizer, loss, model execution, accuracy evaluation,
or download side effect.  The epoch sampler is the human-approved H-003 mapping
recorded by D-010; it is not a Phase 5-frozen training configuration.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import shutil
import tarfile
import tempfile
from typing import BinaryIO, Literal

import torch
from torch import Tensor
from torch.utils.data import Dataset, Sampler


CIFAR10_IMAGE_CHANNELS = 3
CIFAR10_IMAGE_HEIGHT = 32
CIFAR10_IMAGE_WIDTH = 32
CIFAR10_PIXELS_PER_IMAGE = 3_072
CIFAR10_BINARY_RECORD_BYTES = 3_073
CIFAR10_RECORDS_PER_BATCH_FILE = 10_000
CIFAR10_BINARY_BATCH_BYTES = 30_730_000
CIFAR10_TRAIN_SIZE = 50_000
CIFAR10_TEST_SIZE = 10_000
CIFAR10_CLASS_COUNT = 10

CIFAR10_MEAN_255 = (125.3, 123.0, 113.9)
CIFAR10_STD_255 = (63.0, 62.1, 66.7)

CIFAR10_TORONTO_BINARY_URL = (
    "https://cave.cs.toronto.edu/kriz/cifar-10-binary.tar.gz"
)
CIFAR10_TORONTO_BINARY_MD5 = "c32a1d4ab5d03f1284b67883e8d87530"
CIFAR10_CANDIDATE_STREAM_DOMAIN = "densenet-cifar10-loader-v1"

_BINARY_DIRECTORY = "cifar-10-batches-bin"
_TRAIN_BATCH_NAMES = tuple(f"data_batch_{index}.bin" for index in range(1, 6))
_TEST_BATCH_NAMES = ("test_batch.bin",)
_REQUIRED_BATCH_NAMES = _TRAIN_BATCH_NAMES + _TEST_BATCH_NAMES
_UPPER_MD5 = re.compile(r"^[0-9A-F]{32}$")
_UPPER_SHA256 = re.compile(r"^[0-9A-F]{64}$")


@dataclass(frozen=True, slots=True)
class PreparedCifar10SplitVerification:
    """Immutable result of a split-scoped prepared-directory verification."""

    directory: Path
    split: Literal["train", "test"]
    source_archive_sha256: str
    manifest_sha256: str
    files: tuple[tuple[str, int, str], ...]


def _validate_plain_int(name: str, value: int, *, minimum: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in [{minimum}, {maximum}]")


def file_digest(path: Path, algorithm: Literal["md5", "sha256"]) -> str:
    """Return an uppercase streaming digest for a regular file."""

    resolved = Path(path).resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"artifact is not a regular file: {resolved}")
    digest = hashlib.new(algorithm)
    with resolved.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def verify_file_identity(
    path: Path, *, expected_md5: str, expected_sha256: str
) -> dict[str, str | int]:
    """Fail closed unless both independent artifact digests match."""

    normalized_md5 = expected_md5.upper()
    normalized_sha256 = expected_sha256.upper()
    if len(normalized_md5) != 32 or len(normalized_sha256) != 64:
        raise ValueError("expected MD5/SHA256 strings have invalid lengths")
    actual_md5 = file_digest(path, "md5")
    actual_sha256 = file_digest(path, "sha256")
    if actual_md5 != normalized_md5:
        raise ValueError(f"MD5 mismatch for {path}: {actual_md5}")
    if actual_sha256 != normalized_sha256:
        raise ValueError(f"SHA256 mismatch for {path}: {actual_sha256}")
    return {
        "path": str(Path(path).resolve(strict=True)),
        "bytes": Path(path).stat().st_size,
        "md5": actual_md5,
        "sha256": actual_sha256,
    }


def _required_tar_members(archive: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    required_paths = {
        f"{_BINARY_DIRECTORY}/{name}": name for name in _REQUIRED_BATCH_NAMES
    }
    found: dict[str, tarfile.TarInfo] = {}
    for member in archive.getmembers():
        normalized = PurePosixPath(member.name).as_posix()
        if normalized not in required_paths:
            continue
        output_name = required_paths[normalized]
        if output_name in found:
            raise ValueError(f"duplicate required tar member: {normalized}")
        if not member.isfile():
            raise ValueError(f"required tar member is not a regular file: {normalized}")
        if member.size != CIFAR10_BINARY_BATCH_BYTES:
            raise ValueError(
                f"wrong byte size for {normalized}: {member.size}"
            )
        found[output_name] = member
    missing = sorted(set(_REQUIRED_BATCH_NAMES) - set(found))
    if missing:
        raise ValueError(f"missing required CIFAR-10 members: {missing}")
    return found


def _verify_prepared_directory(path: Path) -> dict[str, dict[str, str | int]]:
    if path.is_symlink():
        raise ValueError(f"prepared CIFAR-10 directory may not be a symlink: {path}")
    resolved = path.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError(f"prepared CIFAR-10 path is not a directory: {resolved}")
    files: dict[str, dict[str, str | int]] = {}
    for name in _REQUIRED_BATCH_NAMES:
        unresolved_candidate = resolved / name
        if unresolved_candidate.is_symlink():
            raise ValueError(
                f"prepared CIFAR-10 member may not be a symlink: {unresolved_candidate}"
            )
        candidate = unresolved_candidate.resolve(strict=True)
        if candidate.parent != resolved or not candidate.is_file():
            raise ValueError(f"invalid prepared member: {candidate}")
        size = candidate.stat().st_size
        if size != CIFAR10_BINARY_BATCH_BYTES:
            raise ValueError(f"wrong byte size for {candidate}: {size}")
        files[name] = {
            "bytes": size,
            "sha256": file_digest(candidate, "sha256"),
        }
    return files


def _portable_prepared_manifest(
    *,
    archive_path: Path,
    identity: dict[str, str | int],
    files: dict[str, dict[str, str | int]],
) -> dict[str, object]:
    return {
        "classification": "PHASE2-DERIVED-DATA-CACHE-NOT-FORMAL-FREEZE",
        "source_archive": {
            "filename": Path(archive_path).name,
            "bytes": identity["bytes"],
            "md5": identity["md5"],
            "sha256": identity["sha256"],
        },
        "files": files,
    }


def _verify_prepared_manifest(
    directory: Path, expected: dict[str, object]
) -> None:
    manifest_path = directory / "prepared-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError(f"missing or unsafe prepared manifest: {manifest_path}")
    observed = json.loads(manifest_path.read_text(encoding="utf-8"))
    if observed != expected:
        raise ValueError(f"prepared manifest/content mismatch: {manifest_path}")


def verify_prepared_cifar10_split(
    path: Path,
    *,
    split: Literal["train", "test"],
    expected_archive_sha256: str | None = None,
) -> PreparedCifar10SplitVerification:
    """Verify only the manifest and files needed by one CIFAR-10 split.

    For ``train`` this function never stats, resolves, opens, or hashes
    ``test_batch.bin``. The manifest must still describe the closed six-member
    cache, but only the five training members are accessed on disk.
    """

    if split == "train":
        selected_names = _TRAIN_BATCH_NAMES
    elif split == "test":
        selected_names = _TEST_BATCH_NAMES
    else:
        raise ValueError(f"invalid split: {split!r}")
    unresolved = Path(path)
    if unresolved.is_symlink():
        raise ValueError(f"prepared CIFAR-10 directory may not be a symlink: {unresolved}")
    directory = unresolved.resolve(strict=True)
    if not directory.is_dir():
        raise ValueError(f"prepared CIFAR-10 path is not a directory: {directory}")
    manifest_path = directory / "prepared-manifest.json"
    if manifest_path.is_symlink():
        raise ValueError(f"unsafe prepared manifest: {manifest_path}")
    resolved_manifest = manifest_path.resolve(strict=True)
    if resolved_manifest.parent != directory or not resolved_manifest.is_file():
        raise ValueError(f"missing or unsafe prepared manifest: {manifest_path}")
    raw_manifest = resolved_manifest.read_bytes()
    try:
        manifest = json.loads(raw_manifest.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("prepared manifest is not valid UTF-8 JSON") from error
    if not isinstance(manifest, dict) or set(manifest) != {
        "classification",
        "files",
        "source_archive",
    }:
        raise ValueError("unexpected prepared manifest schema")
    if manifest["classification"] != "PHASE2-DERIVED-DATA-CACHE-NOT-FORMAL-FREEZE":
        raise ValueError("prepared manifest classification mismatch")
    source = manifest["source_archive"]
    if not isinstance(source, dict) or set(source) != {
        "bytes",
        "filename",
        "md5",
        "sha256",
    }:
        raise ValueError("unexpected prepared source-archive schema")
    if (
        isinstance(source["bytes"], bool)
        or not isinstance(source["bytes"], int)
        or source["bytes"] <= 0
        or not isinstance(source["filename"], str)
        or not source["filename"]
        or not isinstance(source["md5"], str)
        or not _UPPER_MD5.fullmatch(source["md5"])
    ):
        raise ValueError("prepared source archive identity is invalid")
    source_sha256 = source["sha256"]
    if not isinstance(source_sha256, str) or not _UPPER_SHA256.fullmatch(source_sha256):
        raise ValueError("prepared source archive SHA256 is invalid")
    if expected_archive_sha256 is not None:
        if not isinstance(expected_archive_sha256, str) or not _UPPER_SHA256.fullmatch(
            expected_archive_sha256
        ):
            raise ValueError("expected source archive SHA256 is invalid")
        if source_sha256 != expected_archive_sha256:
            raise ValueError("prepared source archive differs from the frozen dataset")
    files = manifest["files"]
    if not isinstance(files, dict) or set(files) != set(_REQUIRED_BATCH_NAMES):
        raise ValueError("prepared manifest file set is incomplete")
    for name in _REQUIRED_BATCH_NAMES:
        record = files[name]
        if not isinstance(record, dict) or set(record) != {"bytes", "sha256"}:
            raise ValueError(f"unexpected prepared member schema: {name}")
        if (
            isinstance(record["bytes"], bool)
            or not isinstance(record["bytes"], int)
            or record["bytes"] != CIFAR10_BINARY_BATCH_BYTES
        ):
            raise ValueError(f"wrong manifest byte size for prepared member: {name}")
        if not isinstance(record["sha256"], str) or not _UPPER_SHA256.fullmatch(
            record["sha256"]
        ):
            raise ValueError(f"invalid manifest SHA256 for prepared member: {name}")
    verified: list[tuple[str, int, str]] = []
    for name in selected_names:
        candidate = directory / name
        if candidate.is_symlink():
            raise ValueError(f"prepared CIFAR-10 member may not be a symlink: {candidate}")
        resolved = candidate.resolve(strict=True)
        if resolved.parent != directory or not resolved.is_file():
            raise ValueError(f"invalid prepared member: {resolved}")
        size = resolved.stat().st_size
        if size != CIFAR10_BINARY_BATCH_BYTES:
            raise ValueError(f"wrong byte size for {resolved}: {size}")
        digest = file_digest(resolved, "sha256")
        if digest != files[name]["sha256"]:
            raise ValueError(f"prepared member SHA256 mismatch: {name}")
        verified.append((name, size, digest))
    return PreparedCifar10SplitVerification(
        directory=directory,
        split=split,
        source_archive_sha256=source_sha256,
        manifest_sha256=hashlib.sha256(raw_manifest).hexdigest().upper(),
        files=tuple(verified),
    )


def _tar_member_sha256(
    archive: tarfile.TarFile, member: tarfile.TarInfo
) -> str:
    source = archive.extractfile(member)
    if source is None:
        raise ValueError(f"could not read required tar member: {member.name}")
    digest = hashlib.sha256()
    with source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def prepare_cifar10_binary_archive(
    archive_path: Path,
    destination_root: Path,
    *,
    expected_md5: str,
    expected_sha256: str,
) -> Path:
    """Verify and safely materialize only the six required binary batches."""

    identity = verify_file_identity(
        archive_path,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )
    root = Path(destination_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    final_directory = root / _BINARY_DIRECTORY
    with tarfile.open(Path(archive_path), mode="r:gz") as archive:
        members = _required_tar_members(archive)
        if final_directory.exists():
            files = _verify_prepared_directory(final_directory)
            for name in _REQUIRED_BATCH_NAMES:
                archive_sha256 = _tar_member_sha256(archive, members[name])
                if archive_sha256 != files[name]["sha256"]:
                    raise ValueError(
                        f"prepared file differs from locked archive member: {name}"
                    )
            expected_manifest = _portable_prepared_manifest(
                archive_path=archive_path,
                identity=identity,
                files=files,
            )
            _verify_prepared_manifest(final_directory, expected_manifest)
            return final_directory

        temporary_root = Path(tempfile.mkdtemp(prefix=".cifar10-", dir=root))
        temporary_directory = temporary_root / _BINARY_DIRECTORY
        temporary_directory.mkdir()
        try:
            for name in _REQUIRED_BATCH_NAMES:
                source = archive.extractfile(members[name])
                if source is None:
                    raise ValueError(f"could not read required tar member: {name}")
                with source, (temporary_directory / name).open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
            files = _verify_prepared_directory(temporary_directory)
            manifest = _portable_prepared_manifest(
                archive_path=archive_path,
                identity=identity,
                files=files,
            )
            (temporary_directory / "prepared-manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            temporary_directory.replace(final_directory)
        finally:
            if temporary_root.exists():
                shutil.rmtree(temporary_root)
    return final_directory


@dataclass(frozen=True, slots=True)
class AugmentationDecision:
    """Explicit Torch7-order CIFAR-10+ augmentation choices."""

    horizontal_flip: bool
    crop_x: int
    crop_y: int

    def __post_init__(self) -> None:
        if not isinstance(self.horizontal_flip, bool):
            raise TypeError("horizontal_flip must be bool")
        _validate_plain_int("crop_x", self.crop_x, minimum=0, maximum=8)
        _validate_plain_int("crop_y", self.crop_y, minimum=0, maximum=8)


@dataclass(frozen=True, slots=True)
class AugmentedIndex:
    """A sample index plus scheduling-independent augmentation choices."""

    index: int
    decision: AugmentationDecision


def normalize_cifar10_raw_255(image: Tensor) -> Tensor:
    """Apply the official rounded constants to a CHW raw-0..255 image."""

    if image.shape != (
        CIFAR10_IMAGE_CHANNELS,
        CIFAR10_IMAGE_HEIGHT,
        CIFAR10_IMAGE_WIDTH,
    ):
        raise ValueError(f"expected a [3,32,32] image, got {tuple(image.shape)}")
    if image.dtype != torch.uint8:
        raise TypeError(f"expected torch.uint8 raw pixels, got {image.dtype}")
    output = image.to(dtype=torch.float32)
    for channel, (mean, standard_deviation) in enumerate(
        zip(CIFAR10_MEAN_255, CIFAR10_STD_255, strict=True)
    ):
        output[channel].sub_(mean).div_(standard_deviation)
    return output


def apply_cifar10_train_transform(
    image: Tensor, decision: AugmentationDecision
) -> Tensor:
    """Run Normalize -> HFlip -> zero-pad -> crop in official source order."""

    output = normalize_cifar10_raw_255(image)
    if decision.horizontal_flip:
        output = torch.flip(output, dims=(2,))
    padded = torch.zeros(
        (CIFAR10_IMAGE_CHANNELS, 40, 40), dtype=torch.float32
    )
    padded[:, 4:36, 4:36].copy_(output)
    return padded[
        :,
        decision.crop_y : decision.crop_y + CIFAR10_IMAGE_HEIGHT,
        decision.crop_x : decision.crop_x + CIFAR10_IMAGE_WIDTH,
    ].clone()


def _derive_stream_seed(master_seed: int, epoch: int, stream: str) -> int:
    _validate_plain_int("master_seed", master_seed, minimum=0, maximum=2**63 - 1)
    _validate_plain_int("epoch", epoch, minimum=1, maximum=300)
    payload = (
        f"{CIFAR10_CANDIDATE_STREAM_DOMAIN}|{master_seed}|{epoch}|{stream}"
    ).encode("ascii")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & (
        2**63 - 1
    )


class CandidateCifar10EpochSampler(Sampler[AugmentedIndex]):
    """Worker-scheduling-independent H-003 candidate for one train epoch."""

    def __init__(self, *, size: int, master_seed: int, epoch: int) -> None:
        _validate_plain_int("size", size, minimum=1, maximum=CIFAR10_TRAIN_SIZE)
        _validate_plain_int("master_seed", master_seed, minimum=0, maximum=2**63 - 1)
        _validate_plain_int("epoch", epoch, minimum=1, maximum=300)
        self.size = size
        self.master_seed = master_seed
        self.epoch = epoch

    def __iter__(self) -> Iterator[AugmentedIndex]:
        permutation_generator = torch.Generator().manual_seed(
            _derive_stream_seed(self.master_seed, self.epoch, "permutation")
        )
        augmentation_generator = torch.Generator().manual_seed(
            _derive_stream_seed(self.master_seed, self.epoch, "augmentation")
        )
        permutation = torch.randperm(self.size, generator=permutation_generator)
        for index in permutation.tolist():
            decision = AugmentationDecision(
                horizontal_flip=bool(
                    torch.rand((), generator=augmentation_generator).item() < 0.5
                ),
                crop_x=int(
                    torch.randint(0, 9, (), generator=augmentation_generator).item()
                ),
                crop_y=int(
                    torch.randint(0, 9, (), generator=augmentation_generator).item()
                ),
            )
            yield AugmentedIndex(index=index, decision=decision)

    def __len__(self) -> int:
        return self.size


class Cifar10BinaryDataset(Dataset[tuple[Tensor, int]]):
    """Read exact Toronto binary records from a verified prepared directory."""

    def __init__(self, prepared_directory: Path, *, split: Literal["train", "test"]):
        verification = verify_prepared_cifar10_split(
            prepared_directory, split=split
        )
        self.prepared_directory = verification.directory
        self.split = split
        if split == "train":
            names = _TRAIN_BATCH_NAMES
            self._size = CIFAR10_TRAIN_SIZE
        elif split == "test":
            names = _TEST_BATCH_NAMES
            self._size = CIFAR10_TEST_SIZE
        else:
            raise ValueError(f"invalid split: {split!r}")
        self._paths = tuple(self.prepared_directory / name for name in names)
        self._handles: dict[int, BinaryIO] = {}

    def __len__(self) -> int:
        return self._size

    def _read_record(self, index: int) -> tuple[Tensor, int]:
        _validate_plain_int("index", index, minimum=0, maximum=self._size - 1)
        file_index, record_index = divmod(index, CIFAR10_RECORDS_PER_BATCH_FILE)
        handle = self._handles.get(file_index)
        if handle is None or handle.closed:
            handle = self._paths[file_index].open("rb")
            self._handles[file_index] = handle
        handle.seek(record_index * CIFAR10_BINARY_RECORD_BYTES)
        record = handle.read(CIFAR10_BINARY_RECORD_BYTES)
        if len(record) != CIFAR10_BINARY_RECORD_BYTES:
            raise OSError(f"short CIFAR-10 record read at index {index}")
        label = record[0]
        if not 0 <= label < CIFAR10_CLASS_COUNT:
            raise ValueError(f"invalid CIFAR-10 label {label} at index {index}")
        raw = torch.frombuffer(bytearray(record[1:]), dtype=torch.uint8)
        image = raw.reshape(
            CIFAR10_IMAGE_CHANNELS,
            CIFAR10_IMAGE_HEIGHT,
            CIFAR10_IMAGE_WIDTH,
        )
        return image, label

    def __getitem__(self, key: int | AugmentedIndex) -> tuple[Tensor, int]:
        if isinstance(key, AugmentedIndex):
            if self.split != "train":
                raise TypeError("augmentation keys are valid only for the train split")
            image, label = self._read_record(key.index)
            return apply_cifar10_train_transform(image, key.decision), label
        if self.split == "train":
            raise TypeError(
                "train samples require an explicit AugmentedIndex; ambient RNG is forbidden"
            )
        image, label = self._read_record(key)
        return normalize_cifar10_raw_255(image), label

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()
        self._handles.clear()

    def __getstate__(self) -> dict[str, object]:
        state = self.__dict__.copy()
        state["_handles"] = {}
        return state

    def __del__(self) -> None:
        with suppress(Exception):
            self.close()
