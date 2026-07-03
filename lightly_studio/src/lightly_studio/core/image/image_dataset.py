"""LightlyStudio Image Dataset."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from uuid import UUID

import fsspec
from fsspec.implementations.local import LocalFileSystem
from labelformat.formats import (
    COCOInstanceSegmentationInput,
    COCOObjectDetectionInput,
    LightlyObjectDetectionInput,
    PascalVOCSemanticSegmentationInput,
    YOLOv8ObjectDetectionInput,
)
from labelformat.model.instance_segmentation import (
    InstanceSegmentationInput,
)
from labelformat.model.object_detection import (
    ObjectDetectionInput,
)
from sqlmodel import Session

from lightly_studio.core.dataset import BaseSampleDataset
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.image import add_annotations, add_images
from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.dataset import fsspec_lister
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.evaluation.image_dataset_evaluate import ImageDatasetEvaluate
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    collection_resolver,
    image_resolver,
    tag_resolver,
)
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)


class ImageDataset(BaseSampleDataset[ImageSample]):
    """Image dataset.

    It can be created or loaded using one of the static methods:
    ```python
    dataset = ImageDataset.create()
    dataset = ImageDataset.load()
    dataset = ImageDataset.load_or_create()
    ```

    Samples can be added to the dataset using various methods:
    ```python
    dataset.add_images_from_path(...)
    dataset.add_samples_from_yolo(...)
    dataset.add_samples_from_coco(...)
    dataset.add_samples_from_coco_caption(...)
    dataset.add_samples_from_labelformat(...)
    ```

    The dataset samples can be queried directly by iterating over it or slicing it:
    ```python
    dataset = ImageDataset.load("my_dataset")
    first_ten_samples = dataset[:10]
    for sample in dataset:
        print(sample.file_name)
        sample.metadata["new_key"] = "new_value"
    ```

    For filtering or ordering samples first, use the query interface:
    ```python
    from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField

    dataset = ImageDataset.load("my_dataset")
    query = dataset.match(ImageSampleField.width > 10).order_by(ImageSampleField.file_name)
    for sample in query:
        ...
    ```
    """

    @staticmethod
    def sample_type() -> SampleType:
        """Returns the sample type."""
        return SampleType.IMAGE

    @staticmethod
    def sample_class() -> type[ImageSample]:
        """Returns the sample class."""
        return ImageSample

    def export(self, query: DatasetQuery | None = None) -> ImageDatasetExport:
        """Return an ImageDatasetExport instance which can export the dataset in various formats.

        Args:
            query:
                The dataset query to export. If None, the default query `self.query()` is used.
        """
        if query is None:
            query = self.query()
        return ImageDatasetExport(
            session=self.session,
            dataset_id=self.dataset_id,
            samples=query,
        )

    def get_sample(self, sample_id: UUID) -> ImageSample:
        """Get a single sample from the dataset by its ID.

        Args:
            sample_id: The UUID of the sample to retrieve.

        Returns:
            A single ImageSample object.

        Raises:
            IndexError: If no sample is found with the given sample_id.
        """
        sample = image_resolver.get_by_id(self.session, sample_id=sample_id)

        if sample is None:
            raise IndexError(f"No sample found for sample_id: {sample_id}")
        return ImageSample(inner=sample)

    def add_images_from_path(
        self,
        path: PathLike,
        allowed_extensions: Iterable[str] | None = None,
        embed: bool = True,
        tag_depth: int = 0,
        limit: int | None = None,
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
            limit: Maximum number of samples to load. By default, all samples are loaded.

        Raises:
            NotImplementedError: If tag_depth > 1.
            ValueError: If limit is not None and not greater than 0.
            AllInputFilesFailedError: If every image in the path is missing or broken.
        """
        fsspec_lister.validate_limit(limit)
        # Collect image file paths.
        if allowed_extensions:
            allowed_extensions_set = {ext.lower() for ext in allowed_extensions}
        else:
            allowed_extensions_set = None
        image_paths = list(
            fsspec_lister.iter_files_from_path(
                path=str(path), allowed_extensions=allowed_extensions_set, limit=limit
            )
        )

        logger.info(f"Found {len(image_paths)} images in {path}.")

        # Process images
        created_sample_ids = add_images.load_into_dataset_from_paths(
            session=self.session,
            root_collection_id=self.collection_id,
            image_paths=image_paths,
        )

        if created_sample_ids:
            add_images.tag_samples_by_directory(
                session=self.session,
                collection_id=self.collection_id,
                input_path=path,
                sample_ids=created_sample_ids,
                tag_depth=tag_depth,
            )

        if embed:
            _generate_embeddings_image(
                session=self.session,
                collection_id=self.collection_id,
                sample_ids=created_sample_ids,
            )

    def add_annotations_from_labelformat(
        self,
        input_labels: ObjectDetectionInput | InstanceSegmentationInput,
        images_root: PathLike,
        annotation_source: str,
        embed_annotations: bool = True,
    ) -> None:
        """Attach annotations from a labelformat input to images already in the dataset.

        Images are matched by relative path under ``images_root``. Annotations are grouped
        under an annotation source identified by ``annotation_source``; reusing the same
        annotation_source appends to that source.

        Args:
            input_labels: Labelformat input object (e.g. ``COCOObjectDetectionInput``).
            images_root: Root path used to construct absolute image paths for matching.
            annotation_source: Name of the annotation source.
            embed_annotations: If True, generate embeddings for object-detection annotations.
        """
        missing = add_annotations.add_annotations_from_labelformat(
            session=self.session,
            root_collection_id=self.collection_id,
            input_labels=input_labels,
            images_root=images_root,
            collection_name=annotation_source,
        )
        _log_missing_images(annotation_source=annotation_source, missing_paths=missing)
        _generate_embeddings_annotations(
            session=self.session,
            root_collection_id=self.collection_id,
            annotation_collection_name=annotation_source,
            embed=embed_annotations,
        )

    def add_annotations_from_coco(
        self,
        annotations_json: PathLike,
        images_root: PathLike,
        annotation_source: str,
        annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
        embed_annotations: bool = True,
    ) -> None:
        """Attach COCO annotations to images already in the dataset.

        Args:
            annotations_json: Path to the COCO annotations JSON file.
            images_root: Root path used for matching image filenames.
            annotation_source: Name of the annotation source.
            annotation_type: ``OBJECT_DETECTION`` or ``SEGMENTATION_MASK``.
            embed_annotations: If True, generate embeddings for object-detection annotations.
        """
        label_input: COCOObjectDetectionInput | COCOInstanceSegmentationInput
        if annotation_type == AnnotationType.OBJECT_DETECTION:
            label_input = COCOObjectDetectionInput(input_file=annotations_json)
        elif annotation_type == AnnotationType.SEGMENTATION_MASK:
            label_input = COCOInstanceSegmentationInput(input_file=annotations_json)
        else:
            raise ValueError(f"Invalid annotation type: {annotation_type}")
        self.add_annotations_from_labelformat(
            input_labels=label_input,
            images_root=images_root,
            annotation_source=annotation_source,
            embed_annotations=embed_annotations,
        )

    def add_annotations_from_yolo(
        self,
        data_yaml: PathLike,
        annotation_source: str,
        input_split: str | None = None,
        embed_annotations: bool = True,
    ) -> None:
        """Attach YOLO annotations to images already in the dataset.

        Args:
            data_yaml: Path to the YOLO ``data.yaml`` file.
            annotation_source: Name of the annotation source.
            input_split: Specific split (e.g. ``"train"``). ``None`` loads all splits.
            embed_annotations: If True, generate embeddings for object-detection annotations.
        """
        data_yaml = Path(data_yaml).absolute()
        missing: list[str] = []
        for split in add_annotations.resolve_yolo_splits(
            data_yaml=data_yaml, input_split=input_split
        ):
            label_input = YOLOv8ObjectDetectionInput(input_file=data_yaml, input_split=split)
            missing += add_annotations.add_annotations_from_labelformat(
                session=self.session,
                root_collection_id=self.collection_id,
                input_labels=label_input,
                images_root=label_input._images_dir(),  # noqa: SLF001
                collection_name=annotation_source,
            )
        _log_missing_images(annotation_source=annotation_source, missing_paths=missing)
        _generate_embeddings_annotations(
            session=self.session,
            root_collection_id=self.collection_id,
            annotation_collection_name=annotation_source,
            embed=embed_annotations,
        )

    def add_annotations_from_pascal_voc_segmentations(
        self,
        masks_path: PathLike,
        images_root: PathLike,
        class_id_to_name: Mapping[int, str],
        annotation_source: str,
    ) -> None:
        """Attach Pascal VOC semantic segmentation masks to images already in the dataset.

        Args:
            masks_path: Path to the folder containing the segmentation masks.
            images_root: Root path used for matching image filenames.
            class_id_to_name: Mapping from class IDs to class names.
            annotation_source: Name of the annotation source.
        """
        images_root = _normalize_input_path(path=images_root)
        masks_path = _normalize_input_path(path=masks_path)

        label_input = PascalVOCSemanticSegmentationInput.from_dirs(
            images_dir=images_root,
            masks_dir=masks_path,
            class_id_to_name=class_id_to_name,
        )
        self.add_annotations_from_labelformat(
            input_labels=label_input,
            images_root=images_root,
            annotation_source=annotation_source,
        )

    def add_samples_from_labelformat(  # noqa: PLR0913
        self,
        input_labels: ObjectDetectionInput | InstanceSegmentationInput,
        images_path: PathLike,
        split: str | None = None,
        embed: bool = True,
        annotation_source: str | None = None,
        embed_annotations: bool = True,
        limit: int | None = None,
    ) -> None:
        """Load a dataset from a labelformat object and store in database.

        Args:
            input_labels: The labelformat input object.
            images_path: Path to the folder containing the images.
            split: Optional split name to tag samples (e.g., 'train', 'val').
                If provided, all samples will be tagged with this name.
            embed: If True, generate embeddings for the newly added samples.
            annotation_source: Name of the annotation source to add the annotations
                to. Reusing the same source name appends to that source. If `None`,
                a default source is used.
            embed_annotations: If True, generate embeddings for object-detection annotations.
            limit: Maximum number of samples to load. By default, all samples are loaded.

        Raises:
            ValueError: If limit is not None and not greater than 0.
        """
        fsspec_lister.validate_limit(limit)
        images_path = Path(images_path).absolute()

        created_sample_ids = add_images.load_into_dataset_from_labelformat(
            session=self.session,
            root_collection_id=self.collection_id,
            input_labels=input_labels,
            images_path=images_path,
            collection_name=annotation_source,
            limit=limit,
        )

        _postprocess_created_images(
            session=self.session,
            collection_id=self.collection_id,
            sample_ids=created_sample_ids,
            tag=split,
            embed=embed,
        )
        _generate_embeddings_annotations(
            session=self.session,
            root_collection_id=self.collection_id,
            annotation_collection_name=annotation_source,
            embed=embed_annotations,
        )

    def add_samples_from_yolo(  # noqa: PLR0913
        self,
        data_yaml: PathLike,
        input_split: str | None = None,
        embed: bool = True,
        annotation_source: str | None = None,
        embed_annotations: bool = True,
        limit: int | None = None,
    ) -> None:
        """Load a dataset in YOLO format and store in DB.

        Args:
            data_yaml: Path to the YOLO data.yaml file.
            input_split: The split to load (e.g., 'train', 'val', 'test').
                If None, all available splits will be loaded and assigned a corresponding tag.
            embed: If True, generate embeddings for the newly added samples.
            annotation_source: Name of the annotation source to add the annotations
                to. Reusing the same source name appends to that source. If `None`,
                a default source is used.
            embed_annotations: If True, generate embeddings for object-detection annotations.
            limit: Maximum number of samples to load, in total across all processed
                splits. By default, all samples are loaded.

        Raises:
            ValueError: If limit is not None and not greater than 0.
        """
        fsspec_lister.validate_limit(limit)
        data_yaml = Path(data_yaml).absolute()

        if not data_yaml.is_file() or data_yaml.suffix != ".yaml":
            raise FileNotFoundError(f"YOLO data yaml file not found: '{data_yaml}'")

        # Determine which splits to process
        splits_to_process = add_annotations.resolve_yolo_splits(
            data_yaml=data_yaml, input_split=input_split
        )

        all_created_sample_ids = []
        remaining = limit

        # Process each split
        for split in splits_to_process:
            if remaining is not None and remaining <= 0:
                break
            # Load the dataset using labelformat.
            label_input = YOLOv8ObjectDetectionInput(
                input_file=data_yaml,
                input_split=split,
            )
            images_path = label_input._images_dir()  # noqa: SLF001

            created_sample_ids = add_images.load_into_dataset_from_labelformat(
                session=self.session,
                root_collection_id=self.collection_id,
                input_labels=label_input,
                images_path=images_path,
                collection_name=annotation_source,
                limit=remaining,
            )

            # Tag samples with split name
            _postprocess_created_images(
                session=self.session,
                collection_id=self.collection_id,
                sample_ids=created_sample_ids,
                tag=split,
                embed=False,
            )

            all_created_sample_ids.extend(created_sample_ids)
            if remaining is not None:
                remaining -= len(created_sample_ids)

        # Generate embeddings for all samples at once
        _postprocess_created_images(
            session=self.session,
            collection_id=self.collection_id,
            sample_ids=all_created_sample_ids,
            tag=None,
            embed=embed,
        )
        _generate_embeddings_annotations(
            session=self.session,
            root_collection_id=self.collection_id,
            annotation_collection_name=annotation_source,
            embed=embed_annotations,
        )

    def add_samples_from_coco(  # noqa: PLR0913
        self,
        annotations_json: PathLike,
        images_path: PathLike,
        annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
        split: str | None = None,
        embed: bool = True,
        annotation_source: str | None = None,
        embed_annotations: bool = True,
        limit: int | None = None,
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
            annotation_source: Name of the annotation source to add the annotations
                to. Reusing the same source name appends to that source. If `None`,
                a default source is used.
            embed_annotations: If True, generate embeddings for object-detection annotations.
            limit: Maximum number of samples to load. By default, all samples are loaded.

        Raises:
            ValueError: If limit is not None and not greater than 0.
        """
        fsspec_lister.validate_limit(limit)
        images_path = _normalize_input_path(path=images_path)
        fs, fs_path = fsspec.core.url_to_fs(url=annotations_json)
        if not fs.isfile(fs_path) or not str(annotations_json).endswith(".json"):
            raise FileNotFoundError(f"COCO annotations json file not found: '{annotations_json}'")

        label_input: COCOObjectDetectionInput | COCOInstanceSegmentationInput

        if annotation_type == AnnotationType.OBJECT_DETECTION:
            label_input = COCOObjectDetectionInput(
                input_file=annotations_json,
            )
        elif annotation_type == AnnotationType.SEGMENTATION_MASK:
            label_input = COCOInstanceSegmentationInput(
                input_file=annotations_json,
            )
        else:
            raise ValueError(f"Invalid annotation type: {annotation_type}")

        created_sample_ids = add_images.load_into_dataset_from_labelformat(
            session=self.session,
            root_collection_id=self.collection_id,
            input_labels=label_input,
            images_path=images_path,
            collection_name=annotation_source,
            limit=limit,
        )

        _postprocess_created_images(
            session=self.session,
            collection_id=self.collection_id,
            sample_ids=created_sample_ids,
            tag=split,
            embed=embed,
        )
        _generate_embeddings_annotations(
            session=self.session,
            root_collection_id=self.collection_id,
            annotation_collection_name=annotation_source,
            embed=embed_annotations,
        )

    def add_samples_from_pascal_voc_segmentations(  # noqa: PLR0913
        self,
        images_path: PathLike,
        masks_path: PathLike,
        class_id_to_name: Mapping[int, str],
        split: str | None = None,
        embed: bool = True,
        annotation_source: str | None = None,
        limit: int | None = None,
    ) -> None:
        """Load a Pascal VOC segmentation dataset and store in DB.

        Pascal VOC masks encode class IDs per pixel (semantic segmentation).
        Imported masks are persisted as `AnnotationType.SEGMENTATION_MASK`.
        Query and export workflows should use segmentation mask type filters.

        Args:
            images_path: Path to the folder containing the images.
            masks_path: Path to the folder containing the masks.
            class_id_to_name: Mapping from class IDs to class names.
            split: Optional split name to tag samples (e.g., 'train', 'val').
                If provided, all samples will be tagged with this name.
            embed: If True, generate embeddings for the newly added samples.
            annotation_source: Name of the annotation source to add the annotations
                to. Reusing the same source name appends to that source. If `None`,
                a default source is used.
            limit: Maximum number of samples to load. By default, all samples are loaded.

        Raises:
            ValueError: If limit is not None and not greater than 0.
        """
        fsspec_lister.validate_limit(limit)
        images_path = _normalize_input_path(path=images_path)
        masks_path = _normalize_input_path(path=masks_path)

        label_input = PascalVOCSemanticSegmentationInput.from_dirs(
            images_dir=images_path,
            masks_dir=masks_path,
            class_id_to_name=class_id_to_name,
        )

        created_sample_ids = add_images.load_into_dataset_from_labelformat(
            session=self.session,
            root_collection_id=self.collection_id,
            input_labels=label_input,
            images_path=images_path,
            collection_name=annotation_source,
            limit=limit,
        )

        _postprocess_created_images(
            session=self.session,
            collection_id=self.collection_id,
            sample_ids=created_sample_ids,
            tag=split,
            embed=embed,
        )

    def add_samples_from_lightly(  # noqa: PLR0913
        self,
        input_folder: PathLike,
        images_rel_path: str = "../images",
        split: str | None = None,
        embed: bool = True,
        annotation_source: str | None = None,
        embed_annotations: bool = True,
        limit: int | None = None,
    ) -> None:
        """Load a dataset in Lightly format and store in DB.

        Args:
            input_folder: Path to the folder containing the annotations/predictions.
            images_rel_path: Relative path to images folder from label folder.
            split: Optional split name to tag samples (e.g., 'train', 'val').
                If provided, all samples will be tagged with this name.
            embed: If True, generate embeddings for the newly added samples.
            annotation_source: Name of the annotation source to add the annotations
                to. Reusing the same source name appends to that source. If `None`,
                a default source is used.
            embed_annotations: If True, generate embeddings for object-detection annotations.
            limit: Maximum number of samples to load. By default, all samples are loaded.

        Raises:
            ValueError: If limit is not None and not greater than 0.
        """
        fsspec_lister.validate_limit(limit)
        input_folder = Path(input_folder).absolute()

        # Load the dataset using labelformat.
        label_input = LightlyObjectDetectionInput(
            input_folder=input_folder, images_rel_path=images_rel_path
        )
        images_path = input_folder / images_rel_path

        created_sample_ids = add_images.load_into_dataset_from_labelformat(
            session=self.session,
            root_collection_id=self.collection_id,
            input_labels=label_input,
            images_path=images_path,
            collection_name=annotation_source,
            limit=limit,
        )

        _postprocess_created_images(
            session=self.session,
            collection_id=self.collection_id,
            sample_ids=created_sample_ids,
            tag=split,
            embed=embed,
        )
        _generate_embeddings_annotations(
            session=self.session,
            root_collection_id=self.collection_id,
            annotation_collection_name=annotation_source,
            embed=embed_annotations,
        )

    def add_samples_from_coco_caption(
        self,
        annotations_json: PathLike,
        images_path: PathLike,
        split: str | None = None,
        embed: bool = True,
        limit: int | None = None,
    ) -> None:
        """Load a dataset in COCO caption format and store in DB.

        Args:
            annotations_json: Path to the COCO caption JSON file.
            images_path: Path to the folder containing the images.
            split: Optional split name to tag samples (e.g., 'train', 'val').
                If provided, all samples will be tagged with this name.
            embed: If True, generate embeddings for the newly added samples.
            limit: Maximum number of samples to load. By default, all samples are loaded.

        Raises:
            ValueError: If limit is not None and not greater than 0.
        """
        fsspec_lister.validate_limit(limit)
        annotations_json = Path(annotations_json).absolute()
        images_path = Path(images_path).absolute()

        if not annotations_json.is_file() or annotations_json.suffix != ".json":
            raise FileNotFoundError(f"COCO caption json file not found: '{annotations_json}'")

        created_sample_ids = add_images.load_into_dataset_from_coco_captions(
            session=self.session,
            root_collection_id=self.collection_id,
            annotations_json=annotations_json,
            images_path=images_path,
            limit=limit,
        )

        _postprocess_created_images(
            session=self.session,
            collection_id=self.collection_id,
            sample_ids=created_sample_ids,
            tag=split,
            embed=embed,
        )

    def evaluate(self, query: DatasetQuery | None = None) -> ImageDatasetEvaluate:
        """Return the evaluation facade for this dataset.

        The returned object exposes task-specific evaluation methods, e.g.
        ``dataset.evaluate().object_detection(...)``.

        Args:
            query:
                The dataset query to evaluate. If None, the default query
                ``self.query()`` is used.
        """
        if query is None:
            query = self.query()
        return ImageDatasetEvaluate(
            session=self.session,
            collection_id=self.collection_id,
            sample_ids=[sample.sample_id for sample in query],
        )


def _postprocess_created_images(
    session: Session,
    collection_id: UUID,
    sample_ids: list[UUID],
    tag: str | None,
    embed: bool,
) -> None:
    """Post-process newly created images by generating embeddings and tagging.

    Args:
        session: Database session for resolver operations.
        collection_id: The ID of the collection to associate with the embedding model.
        sample_ids: List of sample IDs to process.
        embed: If True, generate embeddings for the samples.
        tag: Optional tag name to assign to the samples.
    """
    if tag is not None and sample_ids:
        db_tag = tag_resolver.get_or_create_sample_tag_by_name(
            session=session,
            collection_id=collection_id,
            tag_name=tag,
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=session,
            tag_id=db_tag.tag_id,
            sample_ids=sample_ids,
        )

    if embed:
        _generate_embeddings_image(
            session=session,
            collection_id=collection_id,
            sample_ids=sample_ids,
        )


def _normalize_input_path(path: PathLike) -> PathLike:
    """Return absolute path for local inputs and preserve remote URIs."""
    fs, _ = fsspec.core.url_to_fs(url=str(path))
    if isinstance(fs, LocalFileSystem):
        return Path(path).absolute()
    return str(path)


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


def _generate_embeddings_annotations(
    session: Session,
    root_collection_id: UUID,
    annotation_collection_name: str | None,
    embed: bool,
) -> None:
    """Generate and store embeddings for object-detection annotation samples.

    Args:
        session: Database session for resolver operations.
        root_collection_id: The ID of the root collection whose annotation child
            collection should receive embeddings.
        annotation_collection_name: Name of the annotation child collection. If None,
            the default annotation collection name is used.
        embed: If False, this is a no-op.
    """
    if not embed:
        return
    # Get annotation collection if it exists. Otherwise skip embedding generation.
    child_collection_name = annotation_collection_name or SampleType.ANNOTATION.value.lower()
    annotation_collection_id = collection_resolver.get_by_name(
        session=session,
        name=child_collection_name,
        parent_collection_id=root_collection_id,
    )
    if annotation_collection_id is None:
        return
    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = embedding_manager.load_or_get_default_model(
        session=session,
        collection_id=annotation_collection_id,
    )
    if model_id is None:
        logger.warning("No embedding model loaded. Skipping annotation embedding generation.")
        return
    embedding_manager.embed_annotations(
        session=session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )


def _log_missing_images(annotation_source: str, missing_paths: list[str]) -> None:
    """Emit a single warning summarising images skipped due to no DB match."""
    if not missing_paths:
        return
    logger.warning(
        "Annotation source '%s': skipped %d annotation(s) because no matching "
        "image was found in the dataset. First %d unmatched path(s): %s",
        annotation_source,
        len(missing_paths),
        min(5, len(missing_paths)),
        missing_paths[:5],
    )
