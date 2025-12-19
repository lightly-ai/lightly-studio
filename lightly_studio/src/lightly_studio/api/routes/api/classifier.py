"""This module contains the API routes for managing classifiers."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from lightly_studio.db_manager import SessionDep
from lightly_studio.few_shot_classifier.classifier import (
    ExportType,
)
from lightly_studio.few_shot_classifier.classifier_manager import (
    ClassifierManagerProvider,
)
from lightly_studio.models.classifier import EmbeddingClassifier

classifier_router = APIRouter()


class GetNegativeSamplesRequest(BaseModel):
    """Request for getting negative samples for classifier training."""

    positive_sample_ids: list[UUID]
    collection_id: UUID


class GetNegativeSamplesResponse(BaseModel):
    """Response for getting negative samples for classifier training."""

    negative_sample_ids: list[UUID]


@classifier_router.post("/classifiers/get_negative_samples")
def get_negative_samples(
    request: GetNegativeSamplesRequest, session: SessionDep
) -> GetNegativeSamplesResponse:
    """Get negative samples for classifier training.

    Args:
        request: The request containing negative sample parameters.
        session: Database session.

    Returns:
        The response containing negative sample IDs.
    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    negative_samples = classifier_manager.provide_negative_samples(
        session=session,
        collection_id=request.collection_id,
        selected_samples=request.positive_sample_ids,
    )
    # Extract just the sample IDs from the returned Sample objects
    negative_sample_ids = [sample.sample_id for sample in negative_samples]
    return GetNegativeSamplesResponse(negative_sample_ids=negative_sample_ids)


class SamplesToRefineResponse(BaseModel):
    """Response for samples for classifier refinement.

    Maps class names to lists of sample IDs. First class gets high confidence
    samples, second class gets low confidence samples.
    """

    samples: dict[str, list[UUID]]


@classifier_router.get("/classifiers/{classifier_id}/samples_to_refine")
def samples_to_refine(
    classifier_id: UUID,
    collection_id: UUID,
    session: SessionDep,
) -> SamplesToRefineResponse:
    """Get samples for classifier refinement.

    Args:
        classifier_id: The ID of the classifier.
        collection_id: The ID of the collection.
        session: Database session.

    Returns:
        The response containing sample IDs for refinement.
    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    samples = classifier_manager.get_samples_for_fine_tuning(
        session=session, classifier_id=classifier_id, collection_id=collection_id
    )
    return SamplesToRefineResponse(samples=samples)


@classifier_router.get("/classifiers/{classifier_id}/sample_history")
def sample_history(
    classifier_id: UUID,
) -> SamplesToRefineResponse:
    """Get all samples used in the classifier training.

    Args:
        classifier_id: The ID of the classifier.

    Returns:
        The response containing sample IDs used in the training.
    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    samples = classifier_manager.get_annotations(classifier_id=classifier_id)
    return SamplesToRefineResponse(samples=samples)


@classifier_router.post(
    "/classifiers/{classifier_id}/commit_temp_classifier",
)
def commit_temp_classifier(
    classifier_id: UUID,
) -> None:
    """Commit the classifier.

    Args:
        classifier_id: The ID of the classifier.

    Returns:
        None
    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    classifier_manager.commit_temp_classifier(classifier_id=classifier_id)


@classifier_router.delete(
    "/classifiers/{classifier_id}/drop_temp_classifier",
)
def drop_temp_classifier(
    classifier_id: UUID,
) -> None:
    """Drop the classifier.

    Args:
        classifier_id: The ID of the classifier.

    Returns:
        None
    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    classifier_manager.drop_temp_classifier(classifier_id=classifier_id)


class SaveClassifierRequest(BaseModel):
    """Request for saving classifier to a file."""

    file_path: str


@classifier_router.post(
    "/classifiers/{classifier_id}/save_classifier_to_file/{export_type}",
)
def save_classifier_to_file(
    classifier_id: UUID,
    export_type: ExportType,
) -> StreamingResponse:
    """Save the classifier to a file.

    Args:
        classifier_id: The ID of the classifier.
        export_type: The type of export (e.g., "sklearn", "lightly").

    Returns:
        StreamingResponse containing the pickled classifier file.
    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    # Use BytesIO to capture the file content and send it as a response.
    buffer = io.BytesIO()
    classifier_manager.save_classifier_to_buffer(
        classifier_id=classifier_id, buffer=buffer, export_type=export_type
    )
    buffer.seek(0)

    # Get classifier name for the filename
    classifier = classifier_manager.get_classifier_by_id(classifier_id=classifier_id)
    filename = f"{classifier.classifier_name}.pkl"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "application/octet-stream",
        "Access-Control-Expose-Headers": "Content-Disposition",
    }

    return StreamingResponse(buffer, headers=headers, media_type="application/octet-stream")


class LoadClassifierRequest(BaseModel):
    """Request for loading classifier from a file."""

    file_path: str


class LoadClassifierResponse(BaseModel):
    """Response for loading classifier from a file."""

    classifier_id: UUID


@classifier_router.post(
    "/classifiers/load_classifier_from_file",
)
def load_classifier_from_file(
    request: LoadClassifierRequest,
    session: SessionDep,
) -> LoadClassifierResponse:
    """Load the classifier from a file.

    Args:
        request: The request containing the file path.
        session: Database session.

    Returns:
        Response with the ID of the loaded classifier.
    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    classifier = classifier_manager.load_classifier_from_file(
        session=session, file_path=Path(request.file_path)
    )
    return LoadClassifierResponse(classifier_id=classifier.classifier_id)


@classifier_router.post(
    "/classifiers/load_classifier_from_buffer",
)
def load_classifier_from_buffer(
    file: UploadFile,
    session: SessionDep,
) -> UUID:
    """Load a classifier from an uploaded file buffer.

    Args:
        file: The uploaded classifier file.
        session: Database session.

    Returns:
        The ID of the loaded classifier.
    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()

    # Read file into buffer
    buffer = io.BytesIO(file.file.read())

    # Load classifier from buffer
    classifier = classifier_manager.load_classifier_from_buffer(session=session, buffer=buffer)
    return classifier.classifier_id


@classifier_router.post(
    "/classifiers/{classifier_id}/train_classifier",
)
def train_classifier(
    classifier_id: UUID,
    session: SessionDep,
) -> None:
    """Train the classifier.

    Args:
        classifier_id: The ID of the classifier.
        session: Database session.

    Returns:
        None
    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    classifier_manager.train_classifier(session=session, classifier_id=classifier_id)


class UpdateAnnotationsRequest(BaseModel):
    """Request for updating classifier annotations."""

    annotations: dict[str, list[UUID]]


@classifier_router.post(
    "/classifiers/{classifier_id}/update_annotations",
)
def update_classifiers_annotations(
    classifier_id: UUID,
    request: UpdateAnnotationsRequest,
) -> None:
    """Update the annotations for a classifier.

    Args:
        classifier_id: The ID of the classifier.
        request: The request containing the new annotations.

    Returns:
        None

    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    classifier_manager.update_classifiers_annotations(
        classifier_id=classifier_id,
        new_annotations=request.annotations,
    )


class CreateClassifierRequest(BaseModel):
    """Request model for creating a classifier."""

    name: str
    class_list: list[str]
    collection_id: UUID


class CreateClassifierResponse(BaseModel):
    """Response model for creating a classifier."""

    name: str
    classifier_id: str


@classifier_router.post("/classifiers/create")
def create_classifier(
    request: CreateClassifierRequest, session: SessionDep
) -> CreateClassifierResponse:
    """Create a new classifier.

    Args:
        request: The request containing classifier creation parameters.
        session: Database session.

    Returns:
        Response with the name and ID of the classifier.

    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    classifier = classifier_manager.create_classifier(
        session=session,
        name=request.name,
        class_list=request.class_list,
        collection_id=request.collection_id,
    )
    return CreateClassifierResponse(
        name=classifier.few_shot_classifier.name,
        classifier_id=str(classifier.classifier_id),
    )


class GetAllClassifiersResponse(BaseModel):
    """Response model for getting all active classifiers."""

    classifiers: list[EmbeddingClassifier]


@classifier_router.get("/classifiers/get_all_classifiers")
def get_all_classifiers() -> GetAllClassifiersResponse:
    """Get all active classifiers.

    Returns:
        Response with list of tuples containing classifier names and IDs.
    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    classifiers = classifier_manager.get_all_classifiers()
    return GetAllClassifiersResponse(classifiers=classifiers)


@classifier_router.post(
    "/classifiers/{classifier_id}/run_on_collection/{collection_id}",
)
def run_classifier_route(
    classifier_id: UUID,
    collection_id: UUID,
    session: SessionDep,
) -> None:
    """Run the classifier on a collection.

    Args:
        collection_id: The ID of the collection to run the classifier on.
        classifier_id: The ID of the classifier.
        session: Database session.

    Returns:
        None
    """
    classifier_manager = ClassifierManagerProvider.get_classifier_manager()
    classifier_manager.run_classifier(
        session=session,
        classifier_id=classifier_id,
        collection_id=collection_id,
    )
