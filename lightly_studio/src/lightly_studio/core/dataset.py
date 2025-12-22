"""LightlyStudio Dataset."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Generic, Iterable, Iterator
from uuid import UUID

import yaml
from labelformat.formats import (
    COCOInstanceSegmentationInput,
    COCOObjectDetectionInput,
    YOLOv8ObjectDetectionInput,
)
from labelformat.model.instance_segmentation import (
    InstanceSegmentationInput,
)
from labelformat.model.object_detection import (
    ObjectDetectionInput,
)
from sqlmodel import Session
from typing_extensions import TypeVar

from lightly_studio import db_manager
from lightly_studio.api import features
from lightly_studio.core import add_samples, add_videos
from lightly_studio.core.add_videos import VIDEO_EXTENSIONS
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.order_by import OrderByExpression
from lightly_studio.core.image_sample import ImageSample
from lightly_studio.core.sample import Sample
from lightly_studio.dataset import fsspec_lister
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.metadata import compute_similarity, compute_typicality
from lightly_studio.models.annotation.annotation_base import (
    AnnotationType,
)
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import (
    collection_resolver,
    embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
    tag_resolver,
)
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)

# Constants
DEFAULT_DATASET_NAME = "default_dataset"
ALLOWED_YOLO_SPLITS = {"train", "val", "test", "minival"}

_SliceType = slice  # to avoid shadowing built-in slice in type annotations


T = TypeVar("T", bound=Sample)


class Dataset(Generic[T]):
    """A LightlyStudio Dataset.

    It can be created or loaded using one of the static methods:
    ```python
    dataset = Dataset.create()
    dataset = Dataset.load()
    dataset = Dataset.load_or_create()
    ```

    Samples can be added to the dataset using various methods:
    ```python
    dataset.add_images_from_path(...)
    dataset.add_samples_from_yolo(...)
    dataset.add_samples_from_coco(...)
    dataset.add_samples_from_coco_caption(...)
    dataset.add_samples_from_labelformat(...)
    dataset.add_videos_from_path(...)
    ```

    The dataset samples can be queried directly by iterating over it or slicing it:
    ```python
    dataset = Dataset.load("my_dataset")
    first_ten_samples = dataset[:10]
    for sample in dataset:
        print(sample.file_name)
        sample.metadata["new_key"] = "new_value"
    ```

    For filtering or ordering samples first, use the query interface:
    ```python
    from lightly_studio.core.dataset_query.sample_field import SampleField

    dataset = Dataset.load("my_dataset")
    query = dataset.match(SampleField.width > 10).order_by(SampleField.file_name)
    for sample in query:
        ...
    ```
    """

    def __init__(self, collection: CollectionTable, sample_class: type[T]) -> None:
        """Initialize a LightlyStudio Dataset."""
        self._inner = collection
        # TODO(Michal, 09/2025): Do not store the session. Instead, use the
        # dataset object session.
        self.session = db_manager.persistent_session()
        self.sample_class = sample_class

    def __iter__(self) -> Iterator[ImageSample]:
        """Iterate over samples in the dataset."""
        return self.query().__iter__()

    def get_sample(self, sample_id: UUID) -> ImageSample:
        """Get a single sample from the dataset by its ID.

        Args:
            sample_id: The UUID of the sample to retrieve.

        Returns:
            A single ImageTable object.

        Raises:
            IndexError: If no sample is found with the given sample_id.
        """
        sample = image_resolver.get_by_id(self.session, sample_id=sample_id)

        if sample is None:
            raise IndexError(f"No sample found for sample_id: {sample_id}")
        return ImageSample(inner=sample)

    @property
    def dataset_id(self) -> UUID:
        """Get the dataset ID."""
        return self._inner.collection_id

    @property
    def name(self) -> str:
        """Get the dataset name."""
        return self._inner.name

    def query(self) -> DatasetQuery[ImageSample]:
        """Create a DatasetQuery for this dataset.

        Returns:
            A DatasetQuery instance for querying samples in this dataset.
        """
        return DatasetQuery(dataset=self._inner, session=self.session, sample_class=ImageSample)

    def match(self, match_expression: MatchExpression) -> DatasetQuery[ImageSample]:
        """Create a query on the dataset and store a field condition for filtering.

        Args:
            match_expression: Defines the filter.

        Returns:
            DatasetQuery for method chaining.
        """
        return self.query().match(match_expression)

    def order_by(self, *order_by: OrderByExpression) -> DatasetQuery[ImageSample]:
        """Create a query on the dataset and store ordering expressions.

        Args:
            order_by: One or more ordering expressions. They are applied in order.
                E.g. first ordering by sample width and then by sample file_name will
                only order the samples with the same sample width by file_name.

        Returns:
            DatasetQuery for method chaining.
        """
        return self.query().order_by(*order_by)

    def slice(self, offset: int = 0, limit: int | None = None) -> DatasetQuery[ImageSample]:
        """Create a query on the dataset and apply offset and limit to results.

        Args:
            offset: Number of items to skip from beginning (default: 0).
            limit: Maximum number of items to return (None = no limit).

        Returns:
            DatasetQuery for method chaining.
        """
        return self.query().slice(offset, limit)

    def __getitem__(self, key: _SliceType) -> DatasetQuery[ImageSample]:
        """Create a query on the dataset and enable bracket notation for slicing.

        Args:
            key: A slice object (e.g., [10:20], [:50], [100:]).

        Returns:
            DatasetQuery with slice applied.

        Raises:
            TypeError: If key is not a slice object.
            ValueError: If slice contains unsupported features or conflicts with existing slice.
        """
        return self.query()[key]

    def add_videos_from_path(
        self,
        path: PathLike,
        allowed_extensions: Iterable[str] | None = None,
        num_decode_threads: int | None = None,
        embed: bool = True,
    ) -> None:
        """Adding video frames from the specified path to the dataset.

        Args:
            path: Path to the folder containing the videos to add.
            allowed_extensions: An iterable container of allowed video file
                extensions in lowercase, including the leading dot. If None,
            uses default VIDEO_EXTENSIONS.
            num_decode_threads: Optional override for the number of FFmpeg decode threads.
                If omitted, the available CPU cores - 1 (max 16) are used.
            embed: If True, generate embeddings for the newly added videos.
        """
        # Collect video file paths.
        if allowed_extensions:
            allowed_extensions_set = {ext.lower() for ext in allowed_extensions}
        else:
            allowed_extensions_set = VIDEO_EXTENSIONS
        video_paths = list(
            fsspec_lister.iter_files_from_path(
                path=str(path), allowed_extensions=allowed_extensions_set
            )
        )
        logger.info(f"Found {len(video_paths)} videos in {path}.")

        # Process videos.
        created_sample_ids, _ = add_videos.load_into_dataset_from_paths(
            session=self.session,
            dataset_id=self.dataset_id,
            video_paths=video_paths,
            num_decode_threads=num_decode_threads,
        )

        if embed:
            _generate_embeddings_video(
                session=self.session,
                dataset_id=self.dataset_id,
                sample_ids=created_sample_ids,
            )

    def add_images_from_path(
        self,
        path: PathLike,
        allowed_extensions: Iterable[str] | None = None,
        embed: bool = True,
        tag_depth: int = 0,
    ) -> None:
        """Adding images from the specified path to the dataset.

        Args:
            path: Path to the folder containing the images to add.
            allowed_extensions: An iterable container of allowed image file
                extensions.
            embed: If True, generate embeddings for the newly added images.
            tag_depth: Defines the tagging behavior based on directory depth.
                - `tag_depth=0` (default): No automatic tagging is performed.
                - `tag_depth=1`: Automatically creates a tag for each
                  image based on its parent directory's name.

        Raises:
            NotImplementedError: If tag_depth > 1.
        """
        # Collect image file paths.
        if allowed_extensions:
            allowed_extensions_set = {ext.lower() for ext in allowed_extensions}
        else:
            allowed_extensions_set = None
        image_paths = list(
            fsspec_lister.iter_files_from_path(
                path=str(path), allowed_extensions=allowed_extensions_set
            )
        )

        logger.info(f"Found {len(image_paths)} images in {path}.")

        # Process images
        created_sample_ids = add_samples.load_into_dataset_from_paths(
            session=self.session,
            dataset_id=self.dataset_id,
            image_paths=image_paths,
        )

        if created_sample_ids:
            add_samples.tag_samples_by_directory(
                session=self.session,
                collection_id=self.dataset_id,
                input_path=path,
                sample_ids=created_sample_ids,
                tag_depth=tag_depth,
            )

        if embed:
            _generate_embeddings_image(
                session=self.session, collection_id=self.dataset_id, sample_ids=created_sample_ids
            )

    def add_samples_from_labelformat(
        self,
        input_labels: ObjectDetectionInput | InstanceSegmentationInput,
        images_path: PathLike,
        embed: bool = True,
    ) -> None:
        """Load a dataset from a labelformat object and store in database.

        Args:
            input_labels: The labelformat input object.
            images_path: Path to the folder containing the images.
            embed: If True, generate embeddings for the newly added samples.
        """
        if isinstance(images_path, str):
            images_path = Path(images_path)
        images_path = images_path.absolute()

        created_sample_ids = add_samples.load_into_dataset_from_labelformat(
            session=self.session,
            dataset_id=self.dataset_id,
            input_labels=input_labels,
            images_path=images_path,
        )

        if embed:
            _generate_embeddings_image(
                session=self.session, collection_id=self.dataset_id, sample_ids=created_sample_ids
            )

    def add_samples_from_yolo(
        self,
        data_yaml: PathLike,
        input_split: str | None = None,
        embed: bool = True,
    ) -> None:
        """Load a dataset in YOLO format and store in DB.

        Args:
            data_yaml: Path to the YOLO data.yaml file.
            input_split: The split to load (e.g., 'train', 'val', 'test').
                If None, all available splits will be loaded and assigned a corresponding tag.
            embed: If True, generate embeddings for the newly added samples.
        """
        if isinstance(data_yaml, str):
            data_yaml = Path(data_yaml)
        data_yaml = data_yaml.absolute()

        if not data_yaml.is_file() or data_yaml.suffix != ".yaml":
            raise FileNotFoundError(f"YOLO data yaml file not found: '{data_yaml}'")

        # Determine which splits to process
        splits_to_process = _resolve_yolo_splits(data_yaml=data_yaml, input_split=input_split)

        all_created_sample_ids = []

        # Process each split
        for split in splits_to_process:
            # Load the dataset using labelformat.
            label_input = YOLOv8ObjectDetectionInput(
                input_file=data_yaml,
                input_split=split,
            )
            images_path = label_input._images_dir()  # noqa: SLF001

            created_sample_ids = add_samples.load_into_dataset_from_labelformat(
                session=self.session,
                dataset_id=self.dataset_id,
                input_labels=label_input,
                images_path=images_path,
            )

            # Tag samples with split name
            if created_sample_ids:
                tag = tag_resolver.get_or_create_sample_tag_by_name(
                    session=self.session,
                    collection_id=self.dataset_id,
                    tag_name=split,
                )
                tag_resolver.add_sample_ids_to_tag_id(
                    session=self.session,
                    tag_id=tag.tag_id,
                    sample_ids=created_sample_ids,
                )

            all_created_sample_ids.extend(created_sample_ids)

        # Generate embeddings for all samples at once
        if embed:
            _generate_embeddings_image(
                session=self.session,
                collection_id=self.dataset_id,
                sample_ids=all_created_sample_ids,
            )

    def add_samples_from_coco(
        self,
        annotations_json: PathLike,
        images_path: PathLike,
        annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
        split: str | None = None,
        embed: bool = True,
    ) -> None:
        """Load a dataset in COCO Object Detection format and store in DB.

        Args:
            annotations_json: Path to the COCO annotations JSON file.
            images_path: Path to the folder containing the images.
            annotation_type: The type of annotation to be loaded (e.g., 'ObjectDetection',
                'InstanceSegmentation').
            split: Optional split name to tag samples (e.g., 'train', 'val').
                If provided, all samples will be tagged with this name.
            embed: If True, generate embeddings for the newly added samples.
        """
        if isinstance(annotations_json, str):
            annotations_json = Path(annotations_json)
        annotations_json = annotations_json.absolute()

        if not annotations_json.is_file() or annotations_json.suffix != ".json":
            raise FileNotFoundError(f"COCO annotations json file not found: '{annotations_json}'")

        label_input: COCOObjectDetectionInput | COCOInstanceSegmentationInput

        if annotation_type == AnnotationType.OBJECT_DETECTION:
            label_input = COCOObjectDetectionInput(
                input_file=annotations_json,
            )
        elif annotation_type == AnnotationType.INSTANCE_SEGMENTATION:
            label_input = COCOInstanceSegmentationInput(
                input_file=annotations_json,
            )
        else:
            raise ValueError(f"Invalid annotation type: {annotation_type}")

        images_path = Path(images_path).absolute()

        created_sample_ids = add_samples.load_into_dataset_from_labelformat(
            session=self.session,
            dataset_id=self.dataset_id,
            input_labels=label_input,
            images_path=images_path,
        )

        # Tag samples with split name if provided
        if split is not None and created_sample_ids:
            tag = tag_resolver.get_or_create_sample_tag_by_name(
                session=self.session,
                collection_id=self.dataset_id,
                tag_name=split,
            )
            tag_resolver.add_sample_ids_to_tag_id(
                session=self.session,
                tag_id=tag.tag_id,
                sample_ids=created_sample_ids,
            )

        if embed:
            _generate_embeddings_image(
                session=self.session, collection_id=self.dataset_id, sample_ids=created_sample_ids
            )

    def add_samples_from_coco_caption(
        self,
        annotations_json: PathLike,
        images_path: PathLike,
        split: str | None = None,
        embed: bool = True,
    ) -> None:
        """Load a dataset in COCO caption format and store in DB.

        Args:
            annotations_json: Path to the COCO caption JSON file.
            images_path: Path to the folder containing the images.
            split: Optional split name to tag samples (e.g., 'train', 'val').
                If provided, all samples will be tagged with this name.
            embed: If True, generate embeddings for the newly added samples.
        """
        if isinstance(annotations_json, str):
            annotations_json = Path(annotations_json)
        annotations_json = annotations_json.absolute()

        if not annotations_json.is_file() or annotations_json.suffix != ".json":
            raise FileNotFoundError(f"COCO caption json file not found: '{annotations_json}'")

        if isinstance(images_path, str):
            images_path = Path(images_path)
        images_path = images_path.absolute()

        created_sample_ids = add_samples.load_into_dataset_from_coco_captions(
            session=self.session,
            dataset_id=self.dataset_id,
            annotations_json=annotations_json,
            images_path=images_path,
        )

        # Tag samples with split name if provided
        if split is not None and created_sample_ids:
            tag = tag_resolver.get_or_create_sample_tag_by_name(
                session=self.session,
                collection_id=self.dataset_id,
                tag_name=split,
            )
            tag_resolver.add_sample_ids_to_tag_id(
                session=self.session,
                tag_id=tag.tag_id,
                sample_ids=created_sample_ids,
            )

        if embed:
            _generate_embeddings_image(
                session=self.session, collection_id=self.dataset_id, sample_ids=created_sample_ids
            )

    def compute_typicality_metadata(
        self,
        embedding_model_name: str | None = None,
        metadata_name: str = "typicality",
    ) -> None:
        """Computes typicality from embeddings, for K nearest neighbors.

        Args:
            embedding_model_name:
                The name of the embedding model to use. If not given, the default
                embedding model is used.
            metadata_name:
                The name of the metadata to store the typicality values in. If not give, the default
                name "typicality" is used.
        """
        embedding_model_id = embedding_model_resolver.get_by_name(
            session=self.session,
            collection_id=self.dataset_id,
            embedding_model_name=embedding_model_name,
        ).embedding_model_id
        compute_typicality.compute_typicality_metadata(
            session=self.session,
            collection_id=self.dataset_id,
            embedding_model_id=embedding_model_id,
            metadata_name=metadata_name,
        )

    def compute_similarity_metadata(
        self,
        query_tag_name: str,
        embedding_model_name: str | None = None,
        metadata_name: str | None = None,
    ) -> str:
        """Computes similarity with respect to a query tag.

        Args:
            query_tag_name:
                The name of the tag to use for the query.
            embedding_model_name:
                The name of the embedding model to use. If not given, the default
                embedding model is used.
            metadata_name:
                The name of the metadata to store the similarity values in.
                If not given, a name is generated automatically.

        Returns:
            The name of the metadata storing the similarity values.
        """
        embedding_model_id = embedding_model_resolver.get_by_name(
            session=self.session,
            collection_id=self.dataset_id,
            embedding_model_name=embedding_model_name,
        ).embedding_model_id
        query_tag = tag_resolver.get_by_name(
            session=self.session, tag_name=query_tag_name, collection_id=self.dataset_id
        )
        if query_tag is None:
            raise ValueError("Query tag not found")
        return compute_similarity.compute_similarity_metadata(
            session=self.session,
            key_collection_id=self.dataset_id,
            embedding_model_id=embedding_model_id,
            query_tag_id=query_tag.tag_id,
            metadata_name=metadata_name,
        )


def _load_collection(
    name: str | None = None, sample_type: SampleType = SampleType.IMAGE
) -> CollectionTable | None:
    """Load an existing collection.

    Args:
        name: The name of the dataset. If None, a default name is used.
        sample_type: The type of samples in the dataset. Defaults to SampleType.IMAGE.

    Return:
        A collection if it exists, or None if it doesn't.
    """
    if name is None:
        name = "default_dataset"

    collection = collection_resolver.get_by_name(session=db_manager.persistent_session(), name=name)
    if collection is None:
        return None

    # Dataset exists, verify the sample type matches.
    if collection.sample_type != sample_type:
        raise ValueError(
            f"Dataset with name '{name}' already exists with sample type "
            f"'{collection.sample_type.value}', but '{sample_type.value}' was requested."
        )

    # If we have embeddings in the database enable the FSC and embedding search features.
    _enable_embedding_features_if_available(
        session=db_manager.persistent_session(), dataset_id=collection.collection_id
    )
    return collection


def _generate_embeddings_video(
    session: Session,
    dataset_id: UUID,
    sample_ids: list[UUID],
) -> None:
    """Generate and store embeddings for samples.

    Args:
        session: Database session for resolver operations.
        dataset_id: The ID of the dataset to associate with the embedding model.
        sample_ids: List of sample IDs to generate embeddings for.
    """
    if not sample_ids:
        return

    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = embedding_manager.load_or_get_default_model(
        session=session, collection_id=dataset_id
    )
    if model_id is None:
        logger.warning("No embedding model loaded. Skipping embedding generation.")
        return

    embedding_manager.embed_videos(
        session=session,
        collection_id=dataset_id,
        sample_ids=sample_ids,
        embedding_model_id=model_id,
    )

    _mark_embedding_features_enabled()


def _generate_embeddings_image(
    session: Session,
    collection_id: UUID,
    sample_ids: list[UUID],
) -> None:
    """Generate and store embeddings for samples.

    Args:
        session: Database session for resolver operations.
        collection_id: The ID of the collection to associate with the embedding model.
        sample_ids: List of sample IDs to generate embeddings for.
        sample_type: The sample_type to generate embeddings for.
    """
    if not sample_ids:
        return

    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = embedding_manager.load_or_get_default_model(
        session=session, collection_id=collection_id
    )
    if model_id is None:
        logger.warning("No embedding model loaded. Skipping embedding generation.")
        return

    embedding_manager.embed_images(
        session=session,
        collection_id=collection_id,
        sample_ids=sample_ids,
        embedding_model_id=model_id,
    )

    _mark_embedding_features_enabled()


def _mark_embedding_features_enabled() -> None:
    # Mark the embedding search feature as enabled.
    if "embeddingSearchEnabled" not in features.lightly_studio_active_features:
        features.lightly_studio_active_features.append("embeddingSearchEnabled")
    # Mark the FSC feature as enabled.
    if "fewShotClassifierEnabled" not in features.lightly_studio_active_features:
        features.lightly_studio_active_features.append("fewShotClassifierEnabled")


def _resolve_yolo_splits(data_yaml: Path, input_split: str | None) -> list[str]:
    """Determine which YOLO splits to process for the given config."""
    if input_split is not None:
        if input_split not in ALLOWED_YOLO_SPLITS:
            raise ValueError(
                f"Split '{input_split}' not found in config file '{data_yaml}'. "
                f"Allowed splits: {sorted(ALLOWED_YOLO_SPLITS)}"
            )
        return [input_split]

    with data_yaml.open() as f:
        config = yaml.safe_load(f)

    config_keys = config.keys() if isinstance(config, dict) else []
    splits = [key for key in config_keys if key in ALLOWED_YOLO_SPLITS]
    if not splits:
        raise ValueError(f"No splits found in config file '{data_yaml}'")
    return splits


def _are_embeddings_available(session: Session, collection_id: UUID) -> bool:
    """Check if there are any embeddings available for the given dataset.

    Args:
        session: Database session for resolver operations.
        collection_id: The ID of the collection to check for embeddings.

    Returns:
        True if embeddings exist for the collection, False otherwise.
    """
    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = embedding_manager.load_or_get_default_model(
        session=session,
        collection_id=collection_id,
    )
    if model_id is None:
        # No default embedding model loaded for this dataset.
        return False

    return (
        len(
            sample_embedding_resolver.get_all_by_collection_id(
                session=session, collection_id=collection_id, embedding_model_id=model_id
            )
        )
        > 0
    )


def _enable_embedding_features_if_available(session: Session, dataset_id: UUID) -> None:
    """Enable embedding-related features if embeddings are available in the DB.

    Args:
        session: Database session for resolver operations.
        dataset_id: The ID of the dataset to check for embeddings.
    """
    if _are_embeddings_available(session=session, collection_id=dataset_id):
        if "embeddingSearchEnabled" not in features.lightly_studio_active_features:
            features.lightly_studio_active_features.append("embeddingSearchEnabled")
        if "fewShotClassifierEnabled" not in features.lightly_studio_active_features:
            features.lightly_studio_active_features.append("fewShotClassifierEnabled")
