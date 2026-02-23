"""LightlyStudio Image Dataset."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from uuid import UUID

import fsspec
import yaml
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
from lightly_studio.core.image import add_images
from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.dataset import fsspec_lister
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.export.export_dataset import DatasetExport
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    image_resolver,
    tag_resolver,
)
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)

ALLOWED_YOLO_SPLITS = {"train", "val", "test", "minival"}


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

    def export(self, query: DatasetQuery | None = None) -> DatasetExport:
        """Return a DatasetExport instance which can export the dataset in various formats.

        Args:
            query:
                The dataset query to export. If None, the default query `self.query()` is used.
        """
        if query is None:
            query = self.query()
        return DatasetExport(session=self.session, root_dataset_id=self.dataset_id, samples=query)

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
        created_sample_ids = add_images.load_into_dataset_from_paths(
            session=self.session,
            dataset_id=self.dataset_id,
            image_paths=image_paths,
        )

        if created_sample_ids:
            add_images.tag_samples_by_directory(
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
        split: str | None = None,
        embed: bool = True,
    ) -> None:
        """Load a dataset from a labelformat object and store in database.

        Args:
            input_labels: The labelformat input object.
            images_path: Path to the folder containing the images.
            split: Optional split name to tag samples (e.g., 'train', 'val').
                If provided, all samples will be tagged with this name.
            embed: If True, generate embeddings for the newly added samples.
        """
        images_path = Path(images_path).absolute()

        created_sample_ids = add_images.load_into_dataset_from_labelformat(
            session=self.session,
            dataset_id=self.dataset_id,
            input_labels=input_labels,
            images_path=images_path,
        )

        _postprocess_created_images(
            session=self.session,
            collection_id=self.dataset_id,
            sample_ids=created_sample_ids,
            tag=split,
            embed=embed,
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
        data_yaml = Path(data_yaml).absolute()

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

            created_sample_ids = add_images.load_into_dataset_from_labelformat(
                session=self.session,
                dataset_id=self.dataset_id,
                input_labels=label_input,
                images_path=images_path,
            )

            # Tag samples with split name
            _postprocess_created_images(
                session=self.session,
                collection_id=self.dataset_id,
                sample_ids=created_sample_ids,
                tag=split,
                embed=False,
            )

            all_created_sample_ids.extend(created_sample_ids)

        # Generate embeddings for all samples at once
        _postprocess_created_images(
            session=self.session,
            collection_id=self.dataset_id,
            sample_ids=all_created_sample_ids,
            tag=None,
            embed=embed,
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
        annotations_json_str = str(annotations_json)
        images_path_str = str(images_path)
        fs, fs_path = fsspec.core.url_to_fs(url=annotations_json_str)
        if not fs.isfile(fs_path) or not annotations_json_str.endswith(".json"):
            raise FileNotFoundError(
                f"COCO annotations json file not found: '{annotations_json_str}'"
            )

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

        created_sample_ids = add_images.load_into_dataset_from_labelformat(
            session=self.session,
            dataset_id=self.dataset_id,
            input_labels=label_input,
            images_path=images_path_str,
        )

        _postprocess_created_images(
            session=self.session,
            collection_id=self.dataset_id,
            sample_ids=created_sample_ids,
            tag=split,
            embed=embed,
        )

    def add_samples_from_pascal_voc_segmentations(
        self,
        images_path: PathLike,
        masks_path: PathLike,
        class_id_to_name: Mapping[int, str],
        split: str | None = None,
        embed: bool = True,
    ) -> None:
        """Load a semantic segmentation dataset in Pascal VOC format and store in DB.

        Args:
            images_path: Path to the folder containing the images.
            masks_path: Path to the folder containing the masks.
            class_id_to_name: Mapping from class IDs to class names.
            split: Optional split name to tag samples (e.g., 'train', 'val').
                If provided, all samples will be tagged with this name.
            embed: If True, generate embeddings for the newly added samples.
        """
        images_path = Path(images_path).absolute()
        masks_path = Path(masks_path).absolute()

        label_input = PascalVOCSemanticSegmentationInput.from_dirs(
            images_dir=images_path,
            masks_dir=masks_path,
            class_id_to_name=class_id_to_name,
        )

        created_sample_ids = add_images.load_into_dataset_from_labelformat(
            session=self.session,
            dataset_id=self.dataset_id,
            input_labels=label_input,
            images_path=images_path,
            annotation_type=AnnotationType.SEMANTIC_SEGMENTATION,
        )

        _postprocess_created_images(
            session=self.session,
            collection_id=self.dataset_id,
            sample_ids=created_sample_ids,
            tag=split,
            embed=embed,
        )

    def add_samples_from_lightly(
        self,
        input_folder: PathLike,
        images_rel_path: str = "../images",
        split: str | None = None,
        embed: bool = True,
    ) -> None:
        """Load a dataset in Lightly format and store in DB.

        Args:
            input_folder: Path to the folder containing the annotations/predictions.
            images_rel_path: Relative path to images folder from label folder.
            split: Optional split name to tag samples (e.g., 'train', 'val').
                If provided, all samples will be tagged with this name.
            embed: If True, generate embeddings for the newly added samples.
        """
        input_folder = Path(input_folder).absolute()

        # Load the dataset using labelformat.
        label_input = LightlyObjectDetectionInput(
            input_folder=input_folder, images_rel_path=images_rel_path
        )
        images_path = input_folder / images_rel_path

        created_sample_ids = add_images.load_into_dataset_from_labelformat(
            session=self.session,
            dataset_id=self.dataset_id,
            input_labels=label_input,
            images_path=images_path,
        )

        _postprocess_created_images(
            session=self.session,
            collection_id=self.dataset_id,
            sample_ids=created_sample_ids,
            tag=split,
            embed=embed,
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
        annotations_json = Path(annotations_json).absolute()
        images_path = Path(images_path).absolute()

        if not annotations_json.is_file() or annotations_json.suffix != ".json":
            raise FileNotFoundError(f"COCO caption json file not found: '{annotations_json}'")

        created_sample_ids = add_images.load_into_dataset_from_coco_captions(
            session=self.session,
            dataset_id=self.dataset_id,
            annotations_json=annotations_json,
            images_path=images_path,
        )

        _postprocess_created_images(
            session=self.session,
            collection_id=self.dataset_id,
            sample_ids=created_sample_ids,
            tag=split,
            embed=embed,
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
