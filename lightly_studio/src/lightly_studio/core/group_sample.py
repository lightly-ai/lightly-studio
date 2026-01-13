"""Definition of GroupSample class, representing a dataset group sample."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.image_sample import ImageSample
from lightly_studio.core.sample import Sample
from lightly_studio.core.video_sample import VideoSample
from lightly_studio.models.collection import SampleType
from lightly_studio.models.group import GroupTable
from lightly_studio.resolvers import group_resolver, image_resolver, video_resolver


class GroupSample(Sample):
    """TODO Interface to a dataset video sample.

    Many properties of the sample are directly accessible as attributes of this class.
    ```python
    print(f"Sample file name: {sample.file_name}")
    print(f"Sample file path: {sample.file_path_abs}")
    print(f"Sample width: {sample.width}")
    print(f"Sample height: {sample.height}")
    print(f"Sample duration (seconds): {sample.duration_s}")
    print(f"Sample FPS: {sample.fps}")
    ```
    """

    def __init__(self, inner: GroupTable) -> None:
        """Initialize the Sample.

        Args:
            inner: The GroupTable SQLAlchemy model instance.
        """
        self.inner = inner
        super().__init__(sample_table=inner.sample)

    def __getitem__(self, key: str) -> Sample | None:
        """TODO."""
        comp_sample_id, comp_type = group_resolver.get_sample_component_with_type(
            session=self.get_object_session(), sample_id=self.sample_id, key=key
        )
        if comp_sample_id is None:
            return None
        return _create_specific_sample_class(
            session=self.get_object_session(), sample_id=comp_sample_id, sample_type=comp_type
        )


def _create_specific_sample_class(
    session: Session, sample_id: UUID, sample_type: SampleType
) -> Sample:
    if sample_type == SampleType.IMAGE:
        image_table = image_resolver.get_by_id(session=session, sample_id=sample_id)
        if image_table is None:
            raise ValueError(f"Image sample with id '{sample_id}' does not exist.")
        return ImageSample(inner=image_table)
    if sample_type == SampleType.VIDEO:
        video_table = video_resolver.get_by_id(session=session, sample_id=sample_id)
        if video_table is None:
            raise ValueError(f"Video sample with id '{sample_id}' does not exist.")
        return VideoSample(inner=video_table)
    if sample_type == SampleType.GROUP:
        group_table = group_resolver.get_by_id(session=session, sample_id=sample_id)
        if group_table is None:
            raise ValueError(f"Group sample with id '{sample_id}' does not exist.")
        return GroupSample(inner=group_table)
    raise NotImplementedError(
        f"Group component of SampleType '{sample_type}' is not supported yet."
    )
