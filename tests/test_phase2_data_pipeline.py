from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest
import torch
from torch.utils.data import DataLoader, Dataset

import densenet_reproduction.data as data_module
from densenet_reproduction import (
    AugmentationDecision,
    AugmentedIndex,
    CandidateCifar10EpochSampler,
    Cifar10BinaryDataset,
    apply_cifar10_train_transform,
    normalize_cifar10_raw_255,
    prepare_cifar10_binary_archive,
    verify_file_identity,
)


def _digests(path: Path) -> tuple[str, str]:
    payload = path.read_bytes()
    return hashlib.md5(payload).hexdigest(), hashlib.sha256(payload).hexdigest()


def _write_tiny_binary_archive(
    path: Path, *, duplicate: bool = False, required_symlink: bool = False
) -> None:
    payload = bytes(range(16))
    with tarfile.open(path, mode="w:gz") as archive:
        for index, name in enumerate(data_module._REQUIRED_BATCH_NAMES):
            member = tarfile.TarInfo(f"cifar-10-batches-bin/{name}")
            if required_symlink and index == 0:
                member.type = tarfile.SYMTYPE
                member.linkname = "data_batch_2.bin"
                archive.addfile(member)
                continue
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        if duplicate:
            member = tarfile.TarInfo("cifar-10-batches-bin/data_batch_1.bin")
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        ignored_escape = tarfile.TarInfo("../../must-not-be-written")
        ignored_escape.size = len(payload)
        archive.addfile(ignored_escape, io.BytesIO(payload))


def test_artifact_identity_requires_matching_md5_and_sha256(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"phase-2-artifact")
    md5, sha256 = _digests(artifact)

    identity = verify_file_identity(
        artifact, expected_md5=md5, expected_sha256=sha256
    )
    assert identity == {
        "path": str(artifact.resolve()),
        "bytes": 16,
        "md5": md5.upper(),
        "sha256": sha256.upper(),
    }
    with pytest.raises(ValueError, match="MD5 mismatch"):
        verify_file_identity(
            artifact, expected_md5="0" * 32, expected_sha256=sha256
        )
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        verify_file_identity(
            artifact, expected_md5=md5, expected_sha256="0" * 64
        )


def test_safe_archive_preparation_extracts_only_required_regular_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(data_module, "CIFAR10_BINARY_BATCH_BYTES", 16)
    archive = tmp_path / "tiny.tar.gz"
    _write_tiny_binary_archive(archive)
    md5, sha256 = _digests(archive)

    prepared = prepare_cifar10_binary_archive(
        archive,
        tmp_path / "prepared",
        expected_md5=md5,
        expected_sha256=sha256,
    )

    assert prepared.name == "cifar-10-batches-bin"
    assert {path.name for path in prepared.iterdir()} == {
        *data_module._REQUIRED_BATCH_NAMES,
        "prepared-manifest.json",
    }
    assert not (tmp_path / "must-not-be-written").exists()
    manifest = (prepared / "prepared-manifest.json").read_text(encoding="utf-8")
    assert "PHASE2-DERIVED-DATA-CACHE-NOT-FORMAL-FREEZE" in manifest
    assert (
        prepare_cifar10_binary_archive(
            archive,
            tmp_path / "prepared",
            expected_md5=md5,
            expected_sha256=sha256,
        )
        == prepared
    )
    tampered = prepared / "data_batch_1.bin"
    changed = bytearray(tampered.read_bytes())
    changed[0] ^= 1
    tampered.write_bytes(changed)
    with pytest.raises(ValueError, match="differs from locked archive member"):
        prepare_cifar10_binary_archive(
            archive,
            tmp_path / "prepared",
            expected_md5=md5,
            expected_sha256=sha256,
        )


def test_safe_archive_preparation_rejects_duplicate_required_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(data_module, "CIFAR10_BINARY_BATCH_BYTES", 16)
    archive = tmp_path / "duplicate.tar.gz"
    _write_tiny_binary_archive(archive, duplicate=True)
    md5, sha256 = _digests(archive)
    with pytest.raises(ValueError, match="duplicate required tar member"):
        prepare_cifar10_binary_archive(
            archive,
            tmp_path / "prepared",
            expected_md5=md5,
            expected_sha256=sha256,
        )


def test_safe_archive_preparation_rejects_required_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(data_module, "CIFAR10_BINARY_BATCH_BYTES", 16)
    archive = tmp_path / "symlink.tar.gz"
    _write_tiny_binary_archive(archive, required_symlink=True)
    md5, sha256 = _digests(archive)
    with pytest.raises(ValueError, match="not a regular file"):
        prepare_cifar10_binary_archive(
            archive,
            tmp_path / "prepared",
            expected_md5=md5,
            expected_sha256=sha256,
        )


def _raw_coordinate_image() -> torch.Tensor:
    image = torch.empty((3, 32, 32), dtype=torch.uint8)
    x = torch.arange(32, dtype=torch.uint8).view(1, 32).expand(32, 32)
    y = torch.arange(32, dtype=torch.uint8).view(32, 1).expand(32, 32)
    image[0] = x
    image[1] = y
    image[2] = x + y
    return image


def _normalized_scalar(value: int, channel: int) -> torch.Tensor:
    output = torch.tensor(value, dtype=torch.float32)
    output.sub_(data_module.CIFAR10_MEAN_255[channel])
    output.div_(data_module.CIFAR10_STD_255[channel])
    return output


def test_normalization_uses_raw_255_values_and_rounded_official_constants() -> None:
    image = _raw_coordinate_image()
    normalized = normalize_cifar10_raw_255(image)
    assert normalized.dtype == torch.float32
    assert torch.equal(normalized[0, 0, 31], _normalized_scalar(31, 0))
    assert torch.equal(normalized[1, 31, 0], _normalized_scalar(31, 1))
    assert torch.equal(normalized[2, 10, 11], _normalized_scalar(21, 2))


def test_train_transform_is_normalize_then_flip_then_zero_pad_then_crop() -> None:
    image = _raw_coordinate_image()
    output = apply_cifar10_train_transform(
        image,
        AugmentationDecision(horizontal_flip=True, crop_x=0, crop_y=0),
    )
    assert output.shape == (3, 32, 32)
    assert torch.count_nonzero(output[:, :4, :]).item() == 0
    assert torch.count_nonzero(output[:, :, :4]).item() == 0
    assert torch.equal(output[0, 4, 4], _normalized_scalar(31, 0))
    assert torch.equal(output[1, 4, 4], _normalized_scalar(0, 1))
    assert torch.equal(output[2, 4, 4], _normalized_scalar(31, 2))
    assert not torch.equal(output[0, 4, 4], _normalized_scalar(0, 0))


def test_crop_offsets_are_inclusive_and_use_x_for_width_y_for_height() -> None:
    image = _raw_coordinate_image()
    output = apply_cifar10_train_transform(
        image,
        AugmentationDecision(horizontal_flip=False, crop_x=8, crop_y=2),
    )
    assert torch.equal(output[0, 2, 0], _normalized_scalar(4, 0))
    assert torch.equal(output[1, 2, 0], _normalized_scalar(0, 1))
    assert torch.count_nonzero(output[:, :, 28:]).item() == 0


def test_augmentation_decision_rejects_out_of_range_or_ambiguous_values() -> None:
    with pytest.raises(TypeError, match="horizontal_flip"):
        AugmentationDecision(horizontal_flip=1, crop_x=0, crop_y=0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="crop_x"):
        AugmentationDecision(horizontal_flip=False, crop_x=9, crop_y=0)
    with pytest.raises(TypeError, match="crop_y"):
        AugmentationDecision(horizontal_flip=False, crop_x=0, crop_y=True)


def test_candidate_epoch_sampler_is_replayable_complete_and_epoch_specific() -> None:
    first = list(CandidateCifar10EpochSampler(size=17, master_seed=1234, epoch=1))
    replay = list(CandidateCifar10EpochSampler(size=17, master_seed=1234, epoch=1))
    next_epoch = list(CandidateCifar10EpochSampler(size=17, master_seed=1234, epoch=2))

    assert first == replay
    assert first != next_epoch
    assert sorted(item.index for item in first) == list(range(17))
    assert all(0 <= item.decision.crop_x <= 8 for item in first)
    assert all(0 <= item.decision.crop_y <= 8 for item in first)


def _configure_tiny_binary_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, int]:
    records_per_file = 2
    batch_bytes = records_per_file * data_module.CIFAR10_BINARY_RECORD_BYTES
    monkeypatch.setattr(
        data_module, "CIFAR10_RECORDS_PER_BATCH_FILE", records_per_file
    )
    monkeypatch.setattr(data_module, "CIFAR10_BINARY_BATCH_BYTES", batch_bytes)
    monkeypatch.setattr(data_module, "CIFAR10_TRAIN_SIZE", 10)
    monkeypatch.setattr(data_module, "CIFAR10_TEST_SIZE", 2)
    return records_per_file, batch_bytes


def _write_tiny_prepared_directory(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    records_per_file, _ = _configure_tiny_binary_layout(monkeypatch)
    prepared = root / "cifar-10-batches-bin"
    prepared.mkdir()
    for file_number, name in enumerate(data_module._REQUIRED_BATCH_NAMES):
        with (prepared / name).open("wb") as stream:
            for record_number in range(records_per_file):
                label = (2 * file_number + record_number) % 10
                value = (10 * file_number + record_number) % 256
                stream.write(bytes([label]))
                for channel in range(3):
                    stream.write(
                        bytes(
                            (value + 67 * channel + offset) % 256
                            for offset in range(1_024)
                        )
                    )
    files = data_module._verify_prepared_directory(prepared)
    (prepared / "prepared-manifest.json").write_text(
        json.dumps(
            {
                "classification": "PHASE2-DERIVED-DATA-CACHE-NOT-FORMAL-FREEZE",
                "source_archive": {
                    "bytes": 1,
                    "filename": "tiny-generated-fixture.tar.gz",
                    "md5": "0" * 32,
                    "sha256": "D" * 64,
                },
                "files": files,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return prepared


def test_binary_dataset_decodes_chw_zero_based_labels_and_forbids_ambient_rng(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _write_tiny_prepared_directory(tmp_path, monkeypatch)
    train = Cifar10BinaryDataset(prepared, split="train")
    test = Cifar10BinaryDataset(prepared, split="test")
    try:
        assert len(train) == 10
        assert len(test) == 2
        with pytest.raises(TypeError, match="explicit AugmentedIndex"):
            train[0]
        image, label = train[
            AugmentedIndex(
                index=3,
                decision=AugmentationDecision(
                    horizontal_flip=False, crop_x=4, crop_y=4
                ),
            )
        ]
        assert label == 3
        assert image.shape == (3, 32, 32)
        assert torch.equal(image[0, 0, 0], _normalized_scalar(11, 0))
        assert torch.equal(image[0, 0, 1], _normalized_scalar(12, 0))
        assert torch.equal(image[0, 1, 0], _normalized_scalar(43, 0))
        assert torch.equal(image[1, 0, 0], _normalized_scalar(78, 1))
        assert torch.equal(image[2, 0, 0], _normalized_scalar(145, 2))
        test_image, test_label = test[1]
        assert test_label == 1
        assert torch.equal(test_image[0, 0, 0], _normalized_scalar(51, 0))
        with pytest.raises(TypeError, match="train split"):
            test[
                AugmentedIndex(
                    index=0,
                    decision=AugmentationDecision(False, 0, 0),
                )
            ]
    finally:
        train.close()
        test.close()


class _TinyExplicitAugmentationDataset(Dataset[tuple[torch.Tensor, int]]):
    def __init__(self, size: int) -> None:
        self.size = size

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, key: AugmentedIndex) -> tuple[torch.Tensor, int]:
        image = torch.full((3, 32, 32), key.index % 256, dtype=torch.uint8)
        return apply_cifar10_train_transform(image, key.decision), key.index


def _collect_candidate_loader(num_workers: int) -> tuple[torch.Tensor, torch.Tensor]:
    size = 17
    loader = DataLoader(
        _TinyExplicitAugmentationDataset(size),
        batch_size=4,
        sampler=CandidateCifar10EpochSampler(
            size=size, master_seed=1_021_082_110, epoch=7
        ),
        num_workers=num_workers,
        drop_last=False,
    )
    images: list[torch.Tensor] = []
    labels: list[torch.Tensor] = []
    for image_batch, label_batch in loader:
        images.append(image_batch)
        labels.append(label_batch)
    return torch.cat(images), torch.cat(labels)


def test_candidate_pipeline_is_exact_across_zero_and_two_workers() -> None:
    zero_worker = _collect_candidate_loader(0)
    two_workers = _collect_candidate_loader(2)
    assert torch.equal(zero_worker[0], two_workers[0])
    assert torch.equal(zero_worker[1], two_workers[1])
    assert zero_worker[0].shape == (17, 3, 32, 32)
    assert zero_worker[1].unique().numel() == 17
