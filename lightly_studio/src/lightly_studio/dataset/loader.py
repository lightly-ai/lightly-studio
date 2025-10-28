"""Dataset functionality module."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from uuid import UUID

import fsspec
import PIL
from labelformat.formats import (
    COCOInstanceSegmentationInput,
    COCOObjectDetectionInput,
    YOLOv8ObjectDetectionInput,
)
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBoxFormat
from labelformat.model.image import Image
from labelformat.model.instance_segmentation import (
    ImageInstanceSegmentation,
    InstanceSegmentationInput,
)
from labelformat.model.multipolygon import MultiPolygon
from labelformat.model.object_detection import (
    ImageObjectDetection,
    ObjectDetectionInput,
)
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio import db_manager
from lightly_studio.api.features import lightly_studio_active_features
from lightly_studio.api.server import Server
from lightly_studio.dataset import env, fsspec_lister
from lightly_studio.dataset.embedding_generator import EmbeddingGenerator
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    EmbeddingManagerProvider,
)
from lightly_studio.models.annotation.annotation_base import AnnotationCreate
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.dataset import DatasetCreate, DatasetTable
from lightly_studio.models.image import ImageCreate, ImageTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    dataset_resolver,
    image_resolver,
)

# Constants
ANNOTATION_BATCH_SIZE = 64  # Number of annotations to process in a single batch
SAMPLE_BATCH_SIZE = 32  # Number of samples to process in a single batch


@dataclass
class AnnotationProcessingContext:
    """Context for processing annotations for a single sample."""

    dataset_id: UUID
    sample_id: UUID
    label_map: dict[int, UUID]


class DatasetLoader:
    """Class responsible for loading datasets from various sources."""

    def __init__(self) -> None:
        """Initialize the dataset loader."""
        self.session = db_manager.persistent_session()
        self.embedding_manager = EmbeddingManagerProvider.get_embedding_manager()

    def _load_into_dataset(
        self,
        dataset: DatasetTable,
        input_labels: ObjectDetectionInput | InstanceSegmentationInput,
        img_dir: Path,
    ) -> None:
        """Store a loaded dataset in database."""
        # Create label mapping
        label_map = _create_label_map(session=self.session, input_labels=input_labels)

        annotations_to_create: list[AnnotationCreate] = []
        sample_ids: list[UUID] = []
        samples_to_create: list[ImageCreate] = []
        samples_image_data: list[
            tuple[ImageCreate, ImageInstanceSegmentation | ImageObjectDetection]
        ] = []

        for image_data in tqdm(input_labels.get_labels(), desc="Processing images", unit=" images"):
            image: Image = image_data.image  # type: ignore[attr-defined]

            typed_image_data: ImageInstanceSegmentation | ImageObjectDetection = image_data  # type: ignore[assignment]
            sample = ImageCreate(
                file_name=str(image.filename),
                file_path_abs=str(img_dir / image.filename),
                width=image.width,
                height=image.height,
                dataset_id=dataset.dataset_id,
            )
            samples_to_create.append(sample)
            samples_image_data.append((sample, typed_image_data))

            if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
                stored_samples = image_resolver.create_many(
                    session=self.session, samples=samples_to_create
                )
                _process_batch_annotations(
                    session=self.session,
                    stored_samples=stored_samples,
                    samples_data=samples_image_data,
                    dataset_id=dataset.dataset_id,
                    label_map=label_map,
                    annotations_to_create=annotations_to_create,
                    sample_ids=sample_ids,
                )
                samples_to_create.clear()
                samples_image_data.clear()

        if samples_to_create:
            stored_samples = image_resolver.create_many(
                session=self.session, samples=samples_to_create
            )
            _process_batch_annotations(
                session=self.session,
                stored_samples=stored_samples,
                samples_data=samples_image_data,
                dataset_id=dataset.dataset_id,
                label_map=label_map,
                annotations_to_create=annotations_to_create,
                sample_ids=sample_ids,
            )

        # Insert any remaining annotations
        if annotations_to_create:
            annotation_resolver.create_many(session=self.session, annotations=annotations_to_create)

        # Generate embeddings for the dataset.
        _generate_embeddings(
            session=self.session,
            embedding_manager=self.embedding_manager,
            dataset_id=dataset.dataset_id,
            sample_ids=sample_ids,
        )

    def from_yolo(
        self,
        data_yaml_path: str,
        input_split: str = "train",
        task_name: str | None = None,
    ) -> DatasetTable:
        """Load a dataset in YOLO format and store in DB.

        Args:
            data_yaml_path: Path to the YOLO data.yaml file.
            input_split: The split to load (e.g., 'train', 'val').
            task_name: Optional name for the annotation task. If None, a
                default name is generated.

        Returns:
            DatasetTable: The created dataset table entry.
        """
        data_yaml = Path(data_yaml_path).absolute()
        dataset_name = data_yaml.parent.name

        if task_name is None:
            task_name = f"Loaded from YOLO: {data_yaml.name} ({input_split} split)"

        # Load the dataset using labelformat.
        label_input = YOLOv8ObjectDetectionInput(
            input_file=data_yaml,
            input_split=input_split,
        )
        img_dir = label_input._images_dir()  # noqa: SLF001

        return self.from_labelformat(
            input_labels=label_input,
            dataset_name=dataset_name,
            img_dir=str(img_dir),
        )

    def from_coco_object_detections(
        self,
        annotations_json_path: str,
        img_dir: str,
    ) -> DatasetTable:
        """Load a dataset in COCO Object Detection format and store in DB.

        Args:
            annotations_json_path: Path to the COCO annotations JSON file.
            img_dir: Path to the folder containing the images.

        Returns:
            DatasetTable: The created dataset table entry.
        """
        annotations_json = Path(annotations_json_path)
        dataset_name = annotations_json.parent.name

        label_input = COCOObjectDetectionInput(
            input_file=annotations_json,
        )
        img_dir_path = Path(img_dir).absolute()

        return self.from_labelformat(
            input_labels=label_input,
            dataset_name=dataset_name,
            img_dir=str(img_dir_path),
        )

    def from_coco_instance_segmentations(
        self,
        annotations_json_path: str,
        img_dir: str,
    ) -> DatasetTable:
        """Load a dataset in COCO Instance Segmentation format and store in DB.

        Args:
            annotations_json_path: Path to the COCO annotations JSON file.
            img_dir: Path to the folder containing the images.

        Returns:
            DatasetTable: The created dataset table entry.
        """
        annotations_json = Path(annotations_json_path)
        dataset_name = annotations_json.parent.name

        label_input = COCOInstanceSegmentationInput(
            input_file=annotations_json,
        )
        img_dir_path = Path(img_dir).absolute()

        return self.from_labelformat(
            input_labels=label_input,
            dataset_name=dataset_name,
            img_dir=str(img_dir_path),
        )

    def from_labelformat(
        self,
        input_labels: ObjectDetectionInput | InstanceSegmentationInput,
        dataset_name: str,
        img_dir: str,
    ) -> DatasetTable:
        """Load a dataset from a labelformat object and store in database.

        Args:
            input_labels: The labelformat input object.
            dataset_name: The name for the new dataset.
            img_dir: Path to the folder containing the images.

        Returns:
            DatasetTable: The created dataset table entry.
        """
        img_dir_path = Path(img_dir).absolute()

        # Create dataset and annotation task.
        dataset = dataset_resolver.create(
            session=self.session,
            dataset=DatasetCreate(name=dataset_name),
        )

        self._load_into_dataset(
            dataset=dataset,
            input_labels=input_labels,
            img_dir=img_dir_path,
        )
        return dataset

    def from_directory(
        self,
        dataset_name: str,
        img_dir: str,
        allowed_extensions: Iterable[str] = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".bmp",
            ".tiff",
        },
    ) -> DatasetTable:
        """Load a dataset from a folder of images and store in database.

        Args:
            dataset_name: The name for the new dataset.
            img_dir: Path to the folder containing the images.
            allowed_extensions: An iterable container of allowed image file
                extensions.
        """
        # Create dataset.
        dataset = dataset_resolver.create(
            session=self.session,
            dataset=DatasetCreate(name=dataset_name),
        )

        # Collect image file paths with extension filtering.
        allowed_extensions_set = {ext.lower() for ext in allowed_extensions}
        image_paths = list(fsspec_lister.iter_files_from_path(img_dir, allowed_extensions_set))
        print(f"Found {len(image_paths)} images in {img_dir}.")

        # Process images.
        sample_ids = _create_samples_from_paths(
            session=self.session,
            dataset_id=dataset.dataset_id,
            image_paths=image_paths,
        )

        # Generate embeddings for the dataset.
        _generate_embeddings(
            session=self.session,
            embedding_manager=self.embedding_manager,
            dataset_id=dataset.dataset_id,
            sample_ids=list(sample_ids),
        )

        return dataset

    def _validate_has_samples(self) -> None:
        """Validate that there are samples in the database before starting GUI.

        Raises:
            ValueError: If no samples are found in any dataset.
        """
        # Check if any datasets exist
        datasets = dataset_resolver.get_all(session=self.session, offset=0, limit=1)

        if not datasets:
            raise ValueError(
                "No datasets found. Please load a dataset using one of the loader methods "
                "(e.g., from_yolo(), from_directory(), etc.) before starting the GUI."
            )

        # Check if there are any samples in the first dataset
        first_dataset = datasets[0]
        sample_count = image_resolver.count_by_dataset_id(
            session=self.session, dataset_id=first_dataset.dataset_id
        )

        if sample_count == 0:
            raise ValueError(
                "No images have been indexed for the first dataset. "
                "Please ensure your dataset contains valid images and try loading again."
            )

    def start_gui(self) -> None:
        """Launch the web interface for the loaded dataset."""
        self._validate_has_samples()

        server = Server(host=env.LIGHTLY_STUDIO_HOST, port=env.LIGHTLY_STUDIO_PORT)

        print(f"Open the LightlyStudio GUI under: {env.APP_URL}")

        server.start()


def _create_samples_from_paths(
    session: Session,
    dataset_id: UUID,
    image_paths: Iterable[str],
) -> Iterator[UUID]:
    """Create samples from a list of image paths.

    Args:
        session: The database session to use.
        dataset_id: The ID of the dataset to which samples belong.
        image_paths: An iterable of image file paths.

    Yields:
        UUIDs of created sample records.
    """
    samples_to_create: list[ImageCreate] = []

    for image_path in tqdm(
        image_paths,
        desc="Processing images",
        unit=" images",
    ):
        try:
            with fsspec.open(image_path, "rb") as file, PIL.Image.open(file) as img:
                width, height = img.size
        except (FileNotFoundError, PIL.UnidentifiedImageError, OSError):
            continue

        sample = ImageCreate(
            file_name=Path(image_path).name,
            file_path_abs=image_path,
            width=width,
            height=height,
            dataset_id=dataset_id,
        )
        samples_to_create.append(sample)

        # Process batch when it reaches SAMPLE_BATCH_SIZE
        if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
            stored_samples = image_resolver.create_many(session=session, samples=samples_to_create)
            for stored_sample in stored_samples:
                yield stored_sample.sample_id
            samples_to_create = []

    # Handle remaining samples
    if samples_to_create:
        stored_samples = image_resolver.create_many(session=session, samples=samples_to_create)
        for stored_sample in stored_samples:
            yield stored_sample.sample_id


def _create_label_map(
    session: Session,
    input_labels: ObjectDetectionInput | InstanceSegmentationInput,
) -> dict[int, UUID]:
    """Create a mapping of category IDs to annotation label IDs."""
    label_map = {}
    for category in tqdm(
        input_labels.get_categories(),
        desc="Processing categories",
        unit=" categories",
    ):
        label = AnnotationLabelCreate(annotation_label_name=category.name)
        stored_label = annotation_label_resolver.create(session=session, label=label)
        label_map[category.id] = stored_label.annotation_label_id
    return label_map


def _process_object_detection_annotations(
    context: AnnotationProcessingContext,
    image_data: ImageObjectDetection,
) -> list[AnnotationCreate]:
    """Process object detection annotations for a single image."""
    new_annotations = []
    for obj in image_data.objects:
        box = obj.box.to_format(BoundingBoxFormat.XYWH)
        x, y, width, height = box

        new_annotations.append(
            AnnotationCreate(
                dataset_id=context.dataset_id,
                sample_id=context.sample_id,
                annotation_label_id=context.label_map[obj.category.id],
                annotation_type="object_detection",
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                confidence=obj.confidence,
            )
        )
    return new_annotations


def _process_instance_segmentation_annotations(
    context: AnnotationProcessingContext,
    image_data: ImageInstanceSegmentation,
) -> list[AnnotationCreate]:
    """Process instance segmentation annotations for a single image."""
    new_annotations = []
    for obj in image_data.objects:
        segmentation_rle: None | list[int] = None
        if isinstance(obj.segmentation, MultiPolygon):
            box = obj.segmentation.bounding_box().to_format(BoundingBoxFormat.XYWH)
        elif isinstance(obj.segmentation, BinaryMaskSegmentation):
            box = obj.segmentation.bounding_box.to_format(BoundingBoxFormat.XYWH)
            segmentation_rle = obj.segmentation._rle_row_wise  # noqa: SLF001
        else:
            raise ValueError(f"Unsupported segmentation type: {type(obj.segmentation)}")

        x, y, width, height = box

        new_annotations.append(
            AnnotationCreate(
                dataset_id=context.dataset_id,
                sample_id=context.sample_id,
                annotation_label_id=context.label_map[obj.category.id],
                annotation_type="instance_segmentation",
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                segmentation_mask=segmentation_rle,
            )
        )
    return new_annotations


def _process_batch_annotations(  # noqa: PLR0913
    session: Session,
    stored_samples: list[ImageTable],
    samples_data: list[tuple[ImageCreate, ImageInstanceSegmentation | ImageObjectDetection]],
    dataset_id: UUID,
    label_map: dict[int, UUID],
    annotations_to_create: list[AnnotationCreate],
    sample_ids: list[UUID],
) -> None:
    """Process annotations for a batch of samples."""
    for stored_sample, (_, img_data) in zip(stored_samples, samples_data):
        sample_ids.append(stored_sample.sample_id)

        context = AnnotationProcessingContext(
            dataset_id=dataset_id,
            sample_id=stored_sample.sample_id,
            label_map=label_map,
        )

        if isinstance(img_data, ImageInstanceSegmentation):
            new_annotations = _process_instance_segmentation_annotations(
                context=context, image_data=img_data
            )
        elif isinstance(img_data, ImageObjectDetection):
            new_annotations = _process_object_detection_annotations(
                context=context, image_data=img_data
            )
        else:
            raise ValueError(f"Unsupported annotation type: {type(img_data)}")

        annotations_to_create.extend(new_annotations)

        if len(annotations_to_create) >= ANNOTATION_BATCH_SIZE:
            annotation_resolver.create_many(session=session, annotations=annotations_to_create)
            annotations_to_create.clear()


def _generate_embeddings(
    session: Session,
    embedding_manager: EmbeddingManager,
    dataset_id: UUID,
    sample_ids: list[UUID],
) -> None:
    """Generate embeddings for the dataset."""
    # Load an embedding generator and register the model.
    embedding_generator = _load_embedding_generator()

    if embedding_generator:
        lightly_studio_active_features.append("embeddingSearchEnabled")
        embedding_model = embedding_manager.register_embedding_model(
            session=session,
            dataset_id=dataset_id,
            embedding_generator=embedding_generator,
        )
        embedding_manager.embed_images(
            session=session,
            sample_ids=sample_ids,
            embedding_model_id=embedding_model.embedding_model_id,
        )


def _load_embedding_generator() -> EmbeddingGenerator | None:
    """Load the embedding generator.

    Use MobileCLIP if its dependencies have been installed,
    otherwise return None.
    """
    if env.LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE == "EDGE":
        try:
            from lightly_studio.dataset.edge_embedding_generator import (
                EdgeSDKEmbeddingGenerator,
            )

            print("Using LightlyEdge embedding generator.")
            return EdgeSDKEmbeddingGenerator(model_path=env.LIGHTLY_STUDIO_EDGE_MODEL_FILE_PATH)
        except ImportError:
            print("Embedding functionality is disabled.")
            return None
    elif env.LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE == "MOBILE_CLIP":
        try:
            from lightly_studio.dataset.mobileclip_embedding_generator import (
                MobileCLIPEmbeddingGenerator,
            )

            print("Using MobileCLIP embedding generator.")
            return MobileCLIPEmbeddingGenerator()
        except ImportError:
            print("Embedding functionality is disabled.")
            return None
    else:
        print(
            f"Unsupported model type: '{env.LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE}'",
        )
        print("Embedding functionality is disabled.")
        return None
