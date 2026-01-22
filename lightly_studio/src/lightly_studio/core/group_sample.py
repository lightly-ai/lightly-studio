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
    """Interface to a dataset group sample.

    Group components can be accessed via getitem:
    ```python
    print(f"Sample 'component_key' component: {sample['component_key']}")
    ```
    """

    def __init__(self, inner: GroupTable) -> None:
        """Initialize the Sample.

        Args:
            inner: The GroupTable SQLAlchemy model instance.
        """
        self.inner = inner
        super().__init__(sample_table=inner.sample)
