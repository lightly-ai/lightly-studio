import pytest

from scripts import sample_gcs_review


def test_select_sample__selects_rounded_up_fraction() -> None:
    objects = ["object-1", "object-2", "object-3", "object-4"]

    selected = sample_gcs_review.select_sample(objects=objects, fraction=0.33, seed=42)

    assert len(selected) == 2


def test_select_sample__is_reproducible() -> None:
    objects = [f"object-{index}" for index in range(10)]

    first = sample_gcs_review.select_sample(objects=objects, fraction=0.33, seed=7)
    second = sample_gcs_review.select_sample(objects=objects, fraction=0.33, seed=7)

    assert first == second


def test_select_sample__empty_input() -> None:
    assert sample_gcs_review.select_sample(objects=[], fraction=0.33, seed=42) == []


@pytest.mark.parametrize("fraction", [0, -0.1, 1.1])
def test_select_sample__invalid_fraction(fraction: float) -> None:
    with pytest.raises(ValueError, match="fraction"):
        sample_gcs_review.select_sample(objects=["object"], fraction=fraction, seed=42)


def test_destination_url__preserves_nested_path() -> None:
    destination = sample_gcs_review.destination_url(
        source="gs://bucket/source/nested/object.json",
        source_root="gs://bucket/source/",
        destination_root="gs://bucket/pool/",
    )

    assert destination == "gs://bucket/pool/nested/object.json"


def test_destination_url__rejects_object_outside_source() -> None:
    with pytest.raises(ValueError, match="outside the source prefix"):
        sample_gcs_review.destination_url(
            source="gs://bucket/other/object.json",
            source_root="gs://bucket/source/",
            destination_root="gs://bucket/review/",
        )


def test_group_source_objects__complete_triplet() -> None:
    source_root = "gs://bucket/source/"
    objects = [
        f"{source_root}clip.mp4",
        f"{source_root}clip_transcript.json",
        f"{source_root}clip_metadata.json",
    ]

    groups, unmatched = sample_gcs_review.group_source_objects(
        objects=objects, source_root=source_root
    )

    assert unmatched == []
    assert len(groups) == 1
    assert groups[0].stem == "clip"
    assert groups[0].is_complete is True
    assert set(groups[0].files) == set(objects)


def test_group_source_objects__dot_style_companions_complete() -> None:
    source_root = "gs://bucket/source/"
    objects = [
        f"{source_root}folder/clip/clip.mp4",
        f"{source_root}folder/clip/clip.transcript.json",
        f"{source_root}folder/clip/clip.metadata.json",
    ]

    groups, unmatched = sample_gcs_review.group_source_objects(
        objects=objects, source_root=source_root
    )

    assert unmatched == []
    assert len(groups) == 1
    assert groups[0].stem == "folder/clip/clip"
    assert groups[0].is_complete is True
    assert set(groups[0].files) == set(objects)


def test_group_source_objects__mixed_style_companions_complete() -> None:
    source_root = "gs://bucket/source/"
    objects = [
        f"{source_root}clip.mp4",
        f"{source_root}clip.transcript.json",
        f"{source_root}clip_metadata.json",
    ]

    groups, unmatched = sample_gcs_review.group_source_objects(
        objects=objects, source_root=source_root
    )

    assert unmatched == []
    assert groups[0].is_complete is True


def test_group_source_objects__missing_companion_is_incomplete() -> None:
    source_root = "gs://bucket/source/"
    objects = [
        f"{source_root}clip.mp4",
        f"{source_root}clip_transcript.json",
    ]

    groups, unmatched = sample_gcs_review.group_source_objects(
        objects=objects, source_root=source_root
    )

    assert unmatched == []
    assert len(groups) == 1
    assert groups[0].is_complete is False
    assert groups[0].files == objects


def test_video_group__missing_transcript_is_not_shippable() -> None:
    source_root = "gs://bucket/source/"
    objects = [
        f"{source_root}clip.mp4",
        f"{source_root}clip_metadata.json",
    ]

    groups, _ = sample_gcs_review.group_source_objects(objects=objects, source_root=source_root)

    assert groups[0].has_transcript is False
    assert groups[0].is_shippable is False


def test_video_group__missing_metadata_is_not_shippable() -> None:
    source_root = "gs://bucket/source/"
    objects = [
        f"{source_root}clip.mp4",
        f"{source_root}clip_transcript.json",
    ]

    groups, _ = sample_gcs_review.group_source_objects(objects=objects, source_root=source_root)

    assert groups[0].has_metadata is False
    assert groups[0].is_shippable is False


def test_video_group__video_only_is_not_shippable() -> None:
    source_root = "gs://bucket/source/"
    objects = [f"{source_root}clip.mp4"]

    groups, _ = sample_gcs_review.group_source_objects(objects=objects, source_root=source_root)

    assert groups[0].has_metadata is False
    assert groups[0].is_shippable is False


def test_video_group__complete_is_shippable() -> None:
    source_root = "gs://bucket/source/"
    objects = [
        f"{source_root}clip.mp4",
        f"{source_root}clip_transcript.json",
        f"{source_root}clip_metadata.json",
    ]

    groups, _ = sample_gcs_review.group_source_objects(objects=objects, source_root=source_root)

    assert groups[0].is_shippable is True


def test_group_source_objects__preserves_nested_stem() -> None:
    source_root = "gs://bucket/source/"
    objects = [
        f"{source_root}batch1/A_B&C.mp4",
        f"{source_root}batch1/A_B&C_transcript.json",
        f"{source_root}batch1/A_B&C_metadata.json",
    ]

    groups, _ = sample_gcs_review.group_source_objects(objects=objects, source_root=source_root)

    assert groups[0].stem == "batch1/A_B&C"
    assert groups[0].is_complete is True


def test_group_source_objects__orphans_and_strays_unmatched() -> None:
    source_root = "gs://bucket/source/"
    orphan_transcript = f"{source_root}lonely_transcript.json"
    stray = f"{source_root}connection-test.txt"

    groups, unmatched = sample_gcs_review.group_source_objects(
        objects=[orphan_transcript, stray], source_root=source_root
    )

    assert groups == []
    assert unmatched == sorted([orphan_transcript, stray])


def test_split_gcs_url__splits_bucket_and_name() -> None:
    assert sample_gcs_review._split_gcs_url("gs://my-bucket/source/clip.mp4") == (
        "my-bucket",
        "source/clip.mp4",
    )


def test_split_gcs_url__rejects_non_gcs_url() -> None:
    with pytest.raises(ValueError, match="Not a gs:// URL"):
        sample_gcs_review._split_gcs_url("s3://my-bucket/clip.mp4")


def test_split_gcs_url__rejects_missing_object_name() -> None:
    with pytest.raises(ValueError, match="no object name"):
        sample_gcs_review._split_gcs_url("gs://my-bucket")
