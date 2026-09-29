from __future__ import annotations

import fsspec

from lightly_studio.core.mcap import annotation_mcap


def test_annotation_mcap_uri() -> None:
    assert (
        annotation_mcap.annotation_mcap_uri(recording_uri="/data/foo.mcap")
        == "/data/foo_labeled.mcap"
    )
    assert (
        annotation_mcap.annotation_mcap_uri(recording_uri="s3://bucket/runs/foo.mcap")
        == "s3://bucket/runs/foo_labeled.mcap"
    )
    assert (
        annotation_mcap.annotation_mcap_uri(recording_uri="C:\\bags\\foo.mcap")
        == "C:\\bags\\foo_labeled.mcap"
    )


def test_annotation_mcap_uri__custom_suffix() -> None:
    assert (
        annotation_mcap.annotation_mcap_uri(recording_uri="/data/foo.mcap", suffix="_gt")
        == "/data/foo_gt.mcap"
    )


def test_is_annotation_mcap() -> None:
    assert annotation_mcap.is_annotation_mcap(uri="/data/foo_labeled.mcap")
    assert annotation_mcap.is_annotation_mcap(uri="s3://bucket/foo_labeled.mcap")
    assert not annotation_mcap.is_annotation_mcap(uri="/data/foo.mcap")
    assert not annotation_mcap.is_annotation_mcap(uri="/data/foo_labeled_backup.mcap")


def test_annotation_mcap_exists__memory() -> None:
    filesystem = fsspec.filesystem("memory")
    filesystem.pipe("labels/foo_labeled.mcap", b"mcap")

    assert annotation_mcap.annotation_mcap_exists(uri="memory://labels/foo_labeled.mcap")
    assert not annotation_mcap.annotation_mcap_exists(uri="memory://labels/missing_labeled.mcap")
