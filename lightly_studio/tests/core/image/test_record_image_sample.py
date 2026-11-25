from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from lightly_studio.core.image.record_image_sample import RecordImageSample
from lightly_studio.models.sample_query import ImageSampleRecord
from lightly_studio.transport.tag_transport import TagTransport

SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000001")
COLLECTION_ID = UUID("00000000-0000-0000-0000-000000000002")
CREATED_AT = datetime(2026, 1, 2, tzinfo=timezone.utc)
WIDTH = 640


class TestRecordImageSample:
    def test_init(self, mocker: MockerFixture) -> None:
        record = ImageSampleRecord(
            sample_id=SAMPLE_ID,
            collection_id=COLLECTION_ID,
            created_at=CREATED_AT,
            updated_at=CREATED_AT,
            file_name="b.png",
            file_path_abs="/data/b.png",
            width=320,
            height=240,
            tags=["cat"],
        )
        sample = RecordImageSample(record=record, tag_transport=mocker.Mock())

        assert sample.sample_id == SAMPLE_ID
        assert sample.collection_id == COLLECTION_ID
        assert (sample.file_name, sample.file_path_abs) == ("b.png", "/data/b.png")
        assert (sample.width, sample.height) == (320, 240)
        assert sample.created_at == CREATED_AT
        assert sample.tags == {"cat"}

    def test_init__without_tags(self, mocker: MockerFixture) -> None:
        with pytest.raises(ValueError, match="must include the tags"):
            RecordImageSample(record=_record(tags=None), tag_transport=mocker.Mock())

    def test_tags__set(self, mocker: MockerFixture) -> None:
        tag_transport = mocker.create_autospec(TagTransport, instance=True)
        sample = RecordImageSample(record=_record(tags=["cat"]), tag_transport=tag_transport)

        sample.tags = ["dog"]

        assert sample.tags == {"dog"}
        tag_transport.add_to_samples.assert_called_once_with(
            collection_id=COLLECTION_ID, tag_name="dog", sample_ids=[SAMPLE_ID]
        )
        tag_transport.remove_from_samples.assert_called_once_with(
            collection_id=COLLECTION_ID, tag_name="cat", sample_ids=[SAMPLE_ID]
        )

    def test_add_tag(self, mocker: MockerFixture) -> None:
        tag_transport = mocker.create_autospec(TagTransport, instance=True)
        sample = RecordImageSample(record=_record(tags=["cat"]), tag_transport=tag_transport)

        sample.add_tag("dog")

        assert sample.tags == {"cat", "dog"}
        tag_transport.add_to_samples.assert_called_once_with(
            collection_id=COLLECTION_ID, tag_name="dog", sample_ids=[SAMPLE_ID]
        )

    def test_remove_tag(self, mocker: MockerFixture) -> None:
        tag_transport = mocker.create_autospec(TagTransport, instance=True)
        sample = RecordImageSample(record=_record(tags=["cat"]), tag_transport=tag_transport)

        sample.remove_tag("cat")

        assert sample.tags == set()
        tag_transport.remove_from_samples.assert_called_once_with(
            collection_id=COLLECTION_ID, tag_name="cat", sample_ids=[SAMPLE_ID]
        )

    def test_not_supported(self, mocker: MockerFixture) -> None:
        sample = RecordImageSample(record=_record(tags=[]), tag_transport=mocker.Mock())

        with pytest.raises(NotImplementedError):
            _ = sample.metadata
        with pytest.raises(NotImplementedError):
            _ = sample.annotations
        with pytest.raises(NotImplementedError):
            sample.width = 10
        assert sample.width == WIDTH


def _record(tags: list[str] | None) -> ImageSampleRecord:
    return ImageSampleRecord(
        sample_id=SAMPLE_ID,
        collection_id=COLLECTION_ID,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
        file_name="a.png",
        file_path_abs="/data/a.png",
        width=WIDTH,
        height=480,
        tags=tags,
    )
