"""Definition of ImageSample class, representing a dataset image sample."""

from sqlmodel import col

from lightly_studio.core.db_field import DBField
from lightly_studio.core.sample import Sample
from lightly_studio.models.image import ImageTable


class ImageSample(Sample):
    """Interface to a dataset image sample.

    Many properties of the sample are directly accessible as attributes of this class.
    ```python
    print(f"Sample file name: {sample.file_name}")
    print(f"Sample file path: {sample.file_path_abs}")
    print(f"Sample width: {sample.width}")
    print(f"Sample height: {sample.height}")
    ```
    """

    file_name = DBField(col(ImageTable.file_name))
    """Image file name"""
    width = DBField(col(ImageTable.width))
    """Image width (px)"""
    height = DBField(col(ImageTable.height))
    """Image height (px)"""
    file_path_abs = DBField(col(ImageTable.file_path_abs))
    """Absolute path to image"""

    created_at = DBField(col(ImageTable.created_at))
    """Creation timestamp"""
    updated_at = DBField(col(ImageTable.updated_at))
    """Timestamp of the latest update"""

    def __init__(self, inner: ImageTable) -> None:
        """Initialize the Sample.

        Args:
            inner: The ImageTable SQLAlchemy model instance.
        """
        self.inner = inner
        super().__init__(sample_table=inner.sample)
