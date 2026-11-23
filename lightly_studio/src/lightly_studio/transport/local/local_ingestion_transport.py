"""Ingestion transport that adds samples in the same process."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from itertools import islice
from uuid import UUID

from lightly_studio.core.create_sample import CreateSample
from lightly_studio.core.image import add_images
from lightly_studio.core.mcap import add_mcaps, annotation_mcap
from lightly_studio.core.mcap.component_spec import McapComponentSpec
from lightly_studio.core.video import add_videos
from lightly_studio.database import db_manager
from lightly_studio.dataset import fsspec_lister, remote_storage
from lightly_studio.embed import embed_mcap_sequences, embed_samples
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.dynamic_transform import DynamicTransformCreate
from lightly_studio.models.image import AddImagesResult, ImageCreate
from lightly_studio.models.sensor_calibration import SensorCalibrationCreate
from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.models.static_transform import StaticTransformCreate
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    collection_resolver,
    dynamic_transform_resolver,
    group_resolver,
    image_resolver,
    sensor_calibration_resolver,
    sequence_resolver,
    static_transform_resolver,
)

logger = logging.getLogger(__name__)


class LocalIngestionTransport:
    """Implements `IngestionTransport` with the persistent database session."""

    def add_images_from_path(  # noqa: PLR0913
        self,
        collection_id: UUID,
        path: str,
        allowed_extensions: Sequence[str] | None,
        embed: bool,
        tag_depth: int,
        limit: int | None,
    ) -> None:
        """Add the raw images from a path to a collection."""
        fsspec_lister.validate_limit(limit)
        if tag_depth < 0:
            raise ValueError(f"tag_depth must be non-negative, got {tag_depth}.")
        allowed_extensions_set = (
            {ext.lower() for ext in allowed_extensions} if allowed_extensions else None
        )
        # Configure clients before discovery creates and caches a filesystem.
        remote_storage.configure_connections(paths=[path])
        image_paths = list(
            fsspec_lister.iter_files_from_path(
                path=path, allowed_extensions=allowed_extensions_set, limit=limit
            )
        )
        logger.info(f"Found {len(image_paths)} images in {path}.")

        session = db_manager.persistent_session()
        path_to_sample_id = add_images.load_into_dataset_from_paths(
            session=session, root_collection_id=collection_id, image_paths=image_paths
        )
        created_sample_ids = list(path_to_sample_id.values())
        if created_sample_ids:
            add_images.tag_samples_by_directory(
                session=session,
                collection_id=collection_id,
                input_path=path,
                sample_ids=created_sample_ids,
                tag_depth=tag_depth,
            )
        if embed:
            self.embed_images(collection_id=collection_id, sample_ids=created_sample_ids)

    def add_images(self, collection_id: UUID, images: Sequence[ImageCreate]) -> AddImagesResult:
        """Add images with known dimensions to a collection."""
        return add_images.create_images(
            session=db_manager.persistent_session(), collection_id=collection_id, images=images
        )

    def add_directory_tags(
        self, collection_id: UUID, path: str, sample_ids: Sequence[UUID], tag_depth: int
    ) -> None:
        """Tag images with the names of the folders between `path` and the image file."""
        add_images.tag_samples_by_directory(
            session=db_manager.persistent_session(),
            collection_id=collection_id,
            input_path=path,
            sample_ids=list(sample_ids),
            tag_depth=tag_depth,
        )

    def embed_images(self, collection_id: UUID, sample_ids: Sequence[UUID]) -> None:
        """Compute embeddings for images with the default embedding model of the collection.

        The images of the collection without an embedding of the default model get one too,
        so a rerun completes an embedding that failed before.
        """
        session = db_manager.persistent_session()
        ids_to_embed = list(sample_ids)
        default_model_id = collection_embedding_model_resolver.get_default_by_collection_id(
            session=session, collection_id=collection_id
        )
        if default_model_id is not None:
            unembedded_sample_ids = image_resolver.get_unembedded_sample_ids(
                session=session, collection_id=collection_id, embedding_model_id=default_model_id
            )
            ids_to_embed = list(dict.fromkeys([*ids_to_embed, *unembedded_sample_ids]))
        if not ids_to_embed:
            return
        embed_samples.embed_image_samples(
            session=session, collection_id=collection_id, sample_ids=ids_to_embed
        )

    def add_videos_from_path(  # noqa: PLR0913
        self,
        collection_id: UUID,
        path: str,
        allowed_extensions: Sequence[str] | None,
        num_decode_threads: int | None,
        embed: bool,
        embed_frames: bool,
        target_fps: float | None,
        limit: int | None,
    ) -> None:
        """Add the raw videos from a path to a collection."""
        if target_fps is not None and target_fps <= 0:
            raise ValueError(f"target_fps must be greater than 0, got {target_fps}.")
        fsspec_lister.validate_limit(limit)
        video_paths = add_videos.collect_video_file_paths(
            path=path, allowed_extensions=allowed_extensions, limit=limit
        )
        logger.info(f"Found {len(video_paths)} videos in {path}.")

        video_path_to_id, _ = add_videos.load_into_collection_from_paths(
            session=db_manager.persistent_session(),
            collection_id=collection_id,
            video_paths=video_paths,
            num_decode_threads=num_decode_threads,
            target_fps=target_fps,
            embed_frames=embed_frames,
        )
        if embed:
            self.embed_videos(
                collection_id=collection_id, sample_ids=list(video_path_to_id.values())
            )

    def add_videos(
        self,
        collection_id: UUID,
        paths: Sequence[str],
        embed_frames: bool,
        target_fps: float | None,
    ) -> dict[str, UUID]:
        """Add videos from a list of file paths to a collection."""
        video_path_to_id, _ = add_videos.load_into_collection_from_paths(
            session=db_manager.persistent_session(),
            collection_id=collection_id,
            video_paths=paths,
            target_fps=target_fps,
            embed_frames=embed_frames,
        )
        return video_path_to_id

    def embed_videos(self, collection_id: UUID, sample_ids: Sequence[UUID]) -> None:
        """Compute embeddings for videos with the default video embedding model."""
        if not sample_ids:
            return
        embed_samples.embed_video_samples(
            session=db_manager.persistent_session(),
            collection_id=collection_id,
            sample_ids=list(sample_ids),
        )

    def add_group_samples(
        self, collection_id: UUID, groups: Sequence[Mapping[str, CreateSample]]
    ) -> list[UUID]:
        """Add group samples and their component samples to a group collection."""
        session = db_manager.persistent_session()
        comp_collections = collection_resolver.get_group_components(
            session=session, parent_collection_id=collection_id
        )
        for components in groups:
            _validate_components(components=components, comp_collections=comp_collections)
        component_sample_ids = [
            {
                create_sample.create_in_collection(
                    session=session, collection_id=comp_collections[comp_name].collection_id
                )
                for comp_name, create_sample in components.items()
            }
            for components in groups
        ]
        return group_resolver.create_many(
            session=session, collection_id=collection_id, groups=component_sample_ids
        )

    def add_sensor_calibrations(self, rows: Sequence[SensorCalibrationCreate]) -> list[UUID]:
        """Add camera calibrations to MCAP recordings."""
        return sensor_calibration_resolver.create_many(
            session=db_manager.persistent_session(), rows=rows
        )

    def add_static_transforms(self, rows: Sequence[StaticTransformCreate]) -> list[UUID]:
        """Add static transforms between the coordinate frames of MCAP recordings."""
        return static_transform_resolver.create_many(
            session=db_manager.persistent_session(), rows=rows
        )

    def add_dynamic_transforms(self, rows: Sequence[DynamicTransformCreate]) -> list[UUID]:
        """Add dynamic transforms between the coordinate frames of MCAP recordings."""
        return dynamic_transform_resolver.create_many(
            session=db_manager.persistent_session(), rows=rows
        )

    def add_mcaps_from_path(  # noqa: PLR0913
        self,
        collection_id: UUID,
        path: str,
        sync_component: str,
        components: Sequence[McapComponentSpec],
        max_pairing_diff_ns: int,
        limit: int | None,
        reference_frame_ids: Sequence[str] | None,
        embed: bool,
    ) -> None:
        """Index every `.mcap` recording under a path into an MCAP dataset."""
        fsspec_lister.validate_limit(limit)
        # Configure clients before discovery creates and caches a filesystem.
        remote_storage.configure_connections(paths=[path])
        discovered_paths = fsspec_lister.iter_files_from_path(
            path=path, allowed_extensions=add_mcaps.MCAP_EXTENSIONS, limit=None
        )
        mcap_paths = _recording_paths(discovered_paths=discovered_paths, limit=limit)
        logger.info("Found %d MCAP recordings to index in %s.", len(mcap_paths), path)

        session = db_manager.persistent_session()
        sequence_sample_ids = add_mcaps.index_recordings(
            session=session,
            collection_id=collection_id,
            mcap_paths=mcap_paths,
            sync_component=sync_component,
            components=components,
            max_pairing_diff_ns=max_pairing_diff_ns,
            reference_frame_ids=reference_frame_ids,
        )
        if embed:
            embed_mcap_sequences.embed_mcap_sequences(
                session=session,
                collection_id=collection_id,
                sequence_sample_ids=sequence_sample_ids,
            )

    def add_sequence_samples(
        self, sequence_sample_id: UUID, links: Sequence[SampleSequenceLinkCreate]
    ) -> None:
        """Put groups in the slots of an MCAP sequence, in a single commit."""
        sequence_resolver.add_samples(
            session=db_manager.persistent_session(),
            sequence_sample_id=sequence_sample_id,
            links=links,
        )


def _validate_components(
    components: Mapping[str, CreateSample], comp_collections: Mapping[str, CollectionTable]
) -> None:
    for comp_name, create_sample in components.items():
        if comp_name not in comp_collections:
            raise ValueError(f"Component name '{comp_name}' not found in group dataset components.")
        if create_sample.sample_type() != comp_collections[comp_name].sample_type:
            raise ValueError(
                f"Component '{comp_name}' expects samples of type "
                f"'{comp_collections[comp_name].sample_type.name}', "
                f"but got samples of type '{create_sample.sample_type().name}'."
            )


def _recording_paths(discovered_paths: Iterable[str], limit: int | None) -> list[str]:
    """Filter annotation MCAPs before lazily applying the recording limit."""
    recordings = (
        path for path in discovered_paths if not annotation_mcap.is_annotation_mcap(uri=path)
    )
    return list(recordings if limit is None else islice(recordings, limit))
