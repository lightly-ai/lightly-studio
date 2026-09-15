"""Image-only auto-labeling runs and stateless interactive previews."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Union
from uuid import UUID, uuid4

import fsspec
from sqlmodel import Session

from lightly_studio.core.annotation.annotation_create import (
    CreateObjectDetection,
    CreateSegmentationMask,
)
from lightly_studio.models.auto_labeling import (
    AnnotationDescriptor,
    AnnotationPreview,
    AnnotationPreviewBox,
    AnnotationResponse,
    AnnotationTarget,
    AutoLabelBatchRequest,
    AutoLabelBatchResponse,
    BoxPrediction,
    InteractiveAnnotationRequest,
    InteractiveAnnotationResponse,
    MaskPrediction,
    Task,
)
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    collection_resolver,
    grid_filter_sample_ids,
    image_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.services import annotation_prediction
from lightly_studio.services.annotation_model_client import AnnotationModelClient

PendingAnnotation = tuple[UUID, Union[CreateObjectDetection, CreateSegmentationMask]]


def run_batch(session: Session, request: AutoLabelBatchRequest) -> AutoLabelBatchResponse:
    """Resolve scope once, infer, and write a uniquely named annotation source."""
    collection = _image_collection(session=session, collection_id=request.collection_id)
    if not isinstance(request.filter, ImageFilter):
        raise ValueError("Auto-labeling requires an image filter.")
    client = AnnotationModelClient()
    descriptor = client.describe()
    _validate_capability(descriptor=descriptor, task=request.task, conditioning="targets")
    _validate_targets(descriptor=descriptor, targets=request.targets)
    query = grid_filter_sample_ids.build_sample_ids_query(
        session=session, collection_id=request.collection_id, grid_filter=request.filter
    )
    sample_ids = list(session.exec(query).all())
    images = image_resolver.get_many_by_id(session=session, sample_ids=sample_ids)
    pending, processed, unmatched = _infer_targets(
        client=client, descriptor=descriptor, images=images, request=request
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    source_name = f"{descriptor.model_key} {request.task} {timestamp} {uuid4().hex[:8]}"
    source_id = _persist_run(
        session=session,
        collection=collection,
        source_name=source_name,
        pending=pending,
        processed=processed,
    )
    return AutoLabelBatchResponse(
        source_id=source_id,
        source_name=source_name,
        annotations_created=len(pending),
        images_processed=len(processed),
        images_skipped=len(sample_ids) - len(processed),
        unmatched_prompts=unmatched,
    )


def infer_interactive(
    session: Session, request: InteractiveAnnotationRequest
) -> InteractiveAnnotationResponse:
    """Infer a mask preview without modifying any annotation or annotation source."""
    _image_collection(session=session, collection_id=request.collection_id)
    image = image_resolver.get_by_id(session=session, sample_id=request.sample_id)
    if image is None or image.sample.collection_id != request.collection_id:
        raise ValueError("The image does not belong to this collection.")
    client = AnnotationModelClient()
    descriptor = client.describe()
    _validate_capability(descriptor=descriptor, task="segmentation", conditioning="points")
    content = _read_image(image=image)
    start = time.perf_counter()
    result = client.infer(
        descriptor=descriptor,
        task="segmentation",
        images=[content],
        conditioning=json.dumps({"points": [point.model_dump() for point in request.points]}),
    )
    latency = (time.perf_counter() - start) * 1000
    masks = [
        prediction
        for predictions in result.results
        for prediction in predictions
        if isinstance(prediction, MaskPrediction)
    ]
    detections = [
        prediction
        for predictions in result.results
        for prediction in predictions
        if isinstance(prediction, BoxPrediction)
    ]
    converted = [
        annotation_prediction.convert_mask(prediction=mask, image=image, crop_to_bbox=True)
        for mask in sorted(masks, key=lambda value: value.score, reverse=True)
    ]
    mask = next((value for value in converted if value is not None), None)
    class_name = next(
        (
            prediction.class_name.strip()
            for prediction in sorted(detections, key=lambda value: value.score, reverse=True)
            if prediction.class_name.strip()
        ),
        next(
            (
                prediction.class_name.strip()
                for prediction in sorted(masks, key=lambda value: value.score, reverse=True)
                if prediction.class_name.strip()
            ),
            "",
        ),
    )
    preview = (
        None
        if mask is None
        else AnnotationPreview(
            bbox=AnnotationPreviewBox(x=mask.x, y=mask.y, width=mask.width, height=mask.height),
            segmentation_mask=mask.segmentation_mask,
            score=mask.confidence or 0,
            class_name=class_name,
        )
    )
    return InteractiveAnnotationResponse(prediction=preview, latency_ms=latency)


def _infer_targets(
    client: AnnotationModelClient,
    descriptor: AnnotationDescriptor,
    images: list[ImageTable],
    request: AutoLabelBatchRequest,
) -> tuple[list[PendingAnnotation], set[UUID], list[str]]:
    pending: list[PendingAnnotation] = []
    processed: set[UUID] = set()
    unmatched: list[str] = []
    for target in request.targets:
        before = len(pending)
        for offset in range(0, len(images), descriptor.limits.max_batch_size):
            batch = images[offset : offset + descriptor.limits.max_batch_size]
            readable, contents = _read_batch(images=batch)
            if not readable:
                continue
            result = client.infer(
                descriptor=descriptor,
                task=request.task,
                images=contents,
                conditioning=json.dumps({"targets": [target.model_dump()]}),
            )
            processed.update(readable[index].sample_id for index in result.kept_indices)
            pending.extend(
                _convert_batch(result=result, images=readable, request=request, target=target)
            )
        if len(pending) == before:
            unmatched.append(target.prompt)
    return pending, processed, unmatched


def _convert_batch(
    result: AnnotationResponse,
    images: list[ImageTable],
    request: AutoLabelBatchRequest,
    target: AnnotationTarget,
) -> list[PendingAnnotation]:
    pending: list[PendingAnnotation] = []
    for index, predictions in zip(result.kept_indices, result.results):
        image = images[index]
        boxes = [prediction for prediction in predictions if isinstance(prediction, BoxPrediction)]
        selected = list(boxes) if request.task == "object_detection" and boxes else predictions
        for prediction in selected:
            annotation = annotation_prediction.convert_prediction(
                prediction=prediction, image=image, task=request.task
            )
            if annotation is None or prediction.score < request.confidence_threshold:
                continue
            annotation.class_name = target.class_name
            pending.append((image.sample_id, annotation))
    return pending


def _persist_run(
    session: Session,
    collection: CollectionTable,
    source_name: str,
    pending: list[PendingAnnotation],
    processed: set[UUID],
) -> UUID:
    annotations = [
        annotation.to_annotation_create(
            session=session, dataset_id=collection.dataset_id, parent_sample_id=sample_id
        )
        for sample_id, annotation in pending
    ]
    annotation_resolver.create_many(
        session=session,
        parent_collection_id=collection.collection_id,
        annotations=annotations,
        collection_name=source_name,
    )
    source_id = collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
        name=source_name,
    )
    annotation_collection_coverage_resolver.add_many(
        session=session,
        annotation_collection_id=source_id,
        parent_sample_ids=processed,
    )
    session.commit()
    return source_id


def _image_collection(session: Session, collection_id: UUID) -> CollectionTable:
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None or collection.sample_type != SampleType.IMAGE:
        raise ValueError("Auto-labeling is available only for image collections.")
    return collection


def _validate_capability(descriptor: AnnotationDescriptor, task: Task, conditioning: str) -> None:
    if not descriptor.ready:
        raise ValueError(
            "The annotation model is still loading. Check the connection again shortly."
        )
    if (
        f"{task}_image_bytes" not in descriptor.capabilities
        or conditioning not in descriptor.supported_conditioning
    ):
        raise ValueError("The annotation model does not support this task and conditioning.")


def _validate_targets(descriptor: AnnotationDescriptor, targets: list[AnnotationTarget]) -> None:
    for target in targets:
        if not target.prompt.strip() or not target.class_name.strip():
            raise ValueError("Prompts and annotation class names cannot be blank.")
        if descriptor.classes is not None and target.prompt not in descriptor.classes:
            raise ValueError("Choose a prompt from the annotation model's supported classes.")


def _read_image(image: ImageTable) -> bytes:
    filesystem, path = fsspec.core.url_to_fs(image.file_path_abs)
    try:
        return bytes(filesystem.cat_file(path))
    except (OSError, ValueError) as exc:
        raise ValueError("The original image could not be read.") from exc


def _read_batch(images: list[ImageTable]) -> tuple[list[ImageTable], list[bytes]]:
    readable: list[ImageTable] = []
    contents: list[bytes] = []
    for image in images:
        try:
            content = _read_image(image=image)
        except ValueError:
            continue
        readable.append(image)
        contents.append(content)
    return readable, contents
