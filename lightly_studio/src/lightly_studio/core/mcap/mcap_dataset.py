"""LightlyStudio MCAP dataset."""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Iterable, Sequence
from itertools import islice
from pathlib import Path
from uuid import UUID

from typing_extensions import Self

from lightly_studio.analytics import ingest_tracking
from lightly_studio.analytics.ingest_tracking import IngestFormat
from lightly_studio.core import dataset
from lightly_studio.core.dataset import DEFAULT_DATASET_NAME
from lightly_studio.core.mcap import (
    add_labels,
    add_mcaps,
    annotation_mcap,
    dataset_schema,
    folder_labels,
)
from lightly_studio.core.mcap.component import McapComponentSpec
from lightly_studio.core.mcap.group_dataset import McapGroupDataset
from lightly_studio.core.mcap.recording import Recording
from lightly_studio.core.mcap.sequence import McapSequence
from lightly_studio.database import db_manager
from lightly_studio.dataset import fsspec_lister, remote_storage
from lightly_studio.embed import embed_mcap_sequences
from lightly_studio.errors import ExportError
from lightly_studio.export import mcap_scene_update_export
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_sequence_resolver,
    recording_resolver,
)
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)


class McapDataset:
    """A dataset of recordings, indexed from `.mcap` files.

    The components of the dataset are laid out once, and every recording added to it
    is read through the same ones, e.g. one camera and one lidar. A group holds one
    sample per component, all captured at about the same time, and a sequence puts the
    groups of one recording in the order they were recorded in:

    ```python
    import lightly_studio as ls

    components = [
        ls.McapComponentSpec(
            name="front",
            mcap_data_type=ls.McapDataType.VIDEO_FRAME,
            topic="/cam/front/compressed_video",
            camera_info_topic="/cam/front/camera_info",
        ),
        ls.McapComponentSpec(
            name="pcl_front",
            mcap_data_type=ls.McapDataType.POINT_CLOUD,
            topic="/lidar/points",
            frame_id="livox_front_left",
        ),
    ]
    dataset = ls.McapDataset.load_or_create(components=components, name="perception")
    dataset.add_mcaps_from_path(
        path="/data/bags/",
        sync_component="pcl_front",
        components=components,
    )
    ```

    Methods `McapDataset.create()` and `McapDataset.load()` are also available. To index
    a recording step by step instead, use `create_recording`, `group_dataset` and
    `create_sequence`.
    """

    def __init__(self, collection: CollectionTable) -> None:
        """Initialize the dataset.

        Args:
            collection: The root collection of the dataset, of type SEQUENCE.
        """
        self._inner = collection
        # TODO(Michal, 09/2025): Do not store the session. Instead, use the
        # dataset object session.
        self._session = db_manager.persistent_session()
        self._group_dataset: McapGroupDataset | None = None

    @classmethod
    def create(cls, components: Sequence[McapComponentSpec], name: str | None = None) -> Self:
        """Create a dataset for recordings, with the given components.

        Which MCAP channel a component is read from, and which coordinate frame its
        data is in, are not part of this call. They are read from the first recording
        that is indexed, with `McapComponent.update_mcap_definition`.

        Args:
            components: The components of the dataset, one spec per sensor.
            name: The name of the dataset. If None, a default name is used.

        Returns:
            The created dataset.

        Raises:
            ValueError: If `components` is empty, if two components have the same name,
                or if a dataset of that name exists.
        """
        if not components:
            raise ValueError("components must not be empty.")
        # The names are checked before anything is written. The resolver that creates the
        # components also checks them, but only after the collections are committed.
        duplicate_names = _get_duplicate_names(components=components)
        if duplicate_names:
            raise ValueError(
                "components must not repeat a name. These names are used more than once: "
                f"{_format_names(names=duplicate_names)}."
            )
        if name is None:
            name = DEFAULT_DATASET_NAME

        session = db_manager.persistent_session()
        root_collection, group_collection = dataset_schema.create_collections(
            session=session, name=name
        )
        dataset_schema.create_components(
            session=session,
            group_collection_id=group_collection.collection_id,
            components=components,
        )
        session.refresh(root_collection)
        return cls(collection=root_collection)

    @classmethod
    def load(cls, name: str | None = None) -> Self:
        """Load an MCAP dataset that exists.

        The topics of the components are not stored. To index another recording, pass
        `components` to `add_mcaps_from_path`.

        Args:
            name: The name of the dataset. If None, a default name is used.

        Returns:
            The dataset.

        Raises:
            ValueError: If no MCAP dataset of that name exists.
        """
        collection = dataset.load_root_collection(name=name, sample_type=SampleType.SEQUENCE)
        if collection is None:
            raise ValueError(f"Dataset with name '{name}' not found.")
        return cls(collection=collection)

    @classmethod
    def load_or_create(
        cls, components: Sequence[McapComponentSpec], name: str | None = None
    ) -> Self:
        """Create a dataset for recordings, or load the one of that name.

        Args:
            components: The components of the dataset, one spec per sensor. A dataset
                that exists must have exactly these names and data types, in this order.
            name: The name of the dataset. If None, a default name is used.

        Returns:
            The loaded or created dataset.

        Raises:
            ValueError: If `components` is empty, or if a dataset of that name exists
                with other components.
        """
        if not components:
            raise ValueError("components must not be empty.")
        collection = dataset.load_root_collection(name=name, sample_type=SampleType.SEQUENCE)
        if collection is None:
            return cls.create(components=components, name=name)

        mcap_dataset = cls(collection=collection)
        dataset_schema.check_components_match(
            session=db_manager.persistent_session(),
            group_collection_id=mcap_dataset.group_dataset.collection_id,
            components=components,
            dataset_name=collection.name,
        )
        return mcap_dataset

    @property
    def collection_id(self) -> UUID:
        """The ID of the root collection of the dataset."""
        return self._inner.collection_id

    @property
    def dataset_id(self) -> UUID:
        """The ID of the dataset."""
        return self._inner.dataset_id

    @property
    def name(self) -> str:
        """The name of the dataset."""
        return self._inner.name

    @property
    def group_dataset(self) -> McapGroupDataset:
        """The groups of the dataset, one per synchronized tick of a recording."""
        if self._group_dataset is None:
            self._group_dataset = McapGroupDataset(collection=self._group_collection())
        return self._group_dataset

    def add_mcaps_from_path(  # noqa: PLR0913
        self,
        path: PathLike,
        sync_component: str,
        components: Sequence[McapComponentSpec],
        max_pairing_diff_ns: int = add_mcaps.DEFAULT_MAX_PAIRING_DIFF_NS,
        limit: int | None = None,
        reference_frame_ids: Sequence[str] | None = None,
        embed: bool = True,
    ) -> None:
        """Index every `.mcap` recording under a path into the dataset.

        One recording becomes one sequence of groups. Every message of the sync
        component is a tick, and the other components are paired against the tick closest
        in time. A component that cannot be paired to a tick is left out of that group:

        ```python
        dataset.add_mcaps_from_path(
            path="/data/bags/",
            sync_component="pcl_front",
            components=components,
        )
        ```

        Topics are not stored, so `components` is passed on every call. They must be the
        components the dataset was created with.

        A recording that is already indexed is skipped. A recording that cannot be read
        is reported and the others are still indexed. Files named `*_labeled.mcap` are
        annotation MCAPs, not recordings, and are not indexed.

        Args:
            path: A folder of `.mcap` files, a single file, or a glob. It can also be a
                URI into object storage, e.g. `s3://my-bucket/bags/`. It is stored on
                the recording as given, so a relative path stops working once the
                working directory changes.
            sync_component: The name of the component whose messages are the ticks.
            components: The specs the recordings are read through.
            max_pairing_diff_ns: The largest time difference that still pairs a
                component with an anchor tick.
            limit: Maximum number of recordings to index. By default, all are indexed.
            reference_frame_ids: The coordinate frames shown in the viewer, in menu
                order. The first is the default. Each id is the frame string from the
                bag, for example `map` or `CABIN`. When omitted, no frames are
                stored and the viewer keeps each point cloud in its sensor frame.
            embed: If True, generate embeddings for the newly indexed sequences. The
                embedding of a sequence is computed from evenly spaced keyframes of the
                first camera component.

        Raises:
            ValueError: If `components` names other components than the dataset has, if
                `sync_component` is not one of them, if `limit` is not None and not
                greater than 0, or if a reference frame id is empty or repeated.
            AllInputFilesFailedError: If every recording under the path failed.
        """
        source = ingest_tracking.get_source(path=path)
        fsspec_lister.validate_limit(limit)
        # Configure clients before discovery creates and caches a filesystem.
        remote_storage.configure_connections(paths=[str(path)])
        discovered_paths = fsspec_lister.iter_files_from_path(
            path=str(path),
            allowed_extensions=add_mcaps.MCAP_EXTENSIONS,
            limit=None,
        )
        mcap_paths = _recording_paths(
            discovered_paths=discovered_paths,
            limit=limit,
        )
        logger.info("Found %d MCAP recordings to index in %s.", len(mcap_paths), path)

        sequence_sample_ids = add_mcaps.index_recordings(
            dataset=self,
            mcap_paths=mcap_paths,
            sync_component=sync_component,
            components=components,
            max_pairing_diff_ns=max_pairing_diff_ns,
            reference_frame_ids=reference_frame_ids,
        )
        ingest_tracking.track_samples_ingested(
            source=source, sample_type=SampleType.MCAP, ingest_format=IngestFormat.MCAP
        )
        if embed:
            embed_mcap_sequences.embed_mcap_sequences(
                session=self._session,
                collection_id=self.collection_id,
                sequence_sample_ids=sequence_sample_ids,
            )

    def add_labels_from_folder(
        self,
        path: PathLike,
        topic: str,
        suffix: str = annotation_mcap.DEFAULT_ANNOTATION_MCAP_SUFFIX,
        annotation_source: str = add_labels.DEFAULT_ANNOTATION_SOURCE,
    ) -> None:
        """Attach cuboids from annotation MCAPs in a folder to indexed sequences.

        Args:
            path: Folder of annotation MCAPs, or an object-storage URI.
            topic: The SceneUpdate topic in the annotation MCAP.
            suffix: Inserted before `.mcap`. The default is `_labeled`.
            annotation_source: Name of the annotation source that stores the cuboids.
        """
        remote_storage.configure_connections(paths=[str(path)])
        folder_labels.add_labels_from_folder(
            dataset=self, path=path, topic=topic, suffix=suffix, annotation_source=annotation_source
        )

    def export_scene_update_mcaps(  # noqa: PLR0913
        self,
        output_dir: str,
        sequences: Sequence[McapSequence] | None = None,
        annotation_source: str = add_labels.DEFAULT_ANNOTATION_SOURCE,
        target_frame_id: str | None = None,
        topic: str = annotation_mcap.DEFAULT_SCENE_UPDATE_TOPIC,
        suffix: str = annotation_mcap.DEFAULT_ANNOTATION_MCAP_SUFFIX,
    ) -> list[str]:
        """Export cuboids as Foxglove SceneUpdate annotation MCAPs, one per sequence.

        Each file is named after the sequence's recording, with `suffix` inserted before
        `.mcap`. Existing files are never overwritten.

        Args:
            output_dir: Folder to write the files to, or an object-storage URI.
            sequences: The sequences to export. The default is all sequences of the dataset.
            annotation_source: Name of the annotation source to export the cuboids of.
            target_frame_id: The coordinate frame to map every cuboid into. The default is
                the frame that most of the exported cuboids are stored in. Without cuboids,
                it is the first reference frame that all exported recordings share.
            topic: The topic to write the SceneUpdate messages on.
            suffix: Inserted before `.mcap`. The default is `_labeled`.

        Returns:
            The URIs of the written files, in the order of the exported sequences.

        Raises:
            ValueError: If the dataset has no annotation source of that name.
            ExportError: If a destination file exists, two sequences map to the same file
                name, or no `target_frame_id` is given and the recordings share no frame.

        Example:
            ```python
            import lightly_studio as ls

            dataset = ls.McapDataset.load(name="perception")
            uris = dataset.export_scene_update_mcaps(output_dir="s3://bucket/labels")
            ```
        """
        exported = self.get_sequences() if sequences is None else list(sequences)
        sequence_ids = [sequence.sample_id for sequence in exported]
        annotation_collection = self._annotation_collection(annotation_source=annotation_source)
        if target_frame_id is None:
            target_frame_id = self._default_target_frame_id(sequence_ids=sequence_ids)
        with tempfile.TemporaryDirectory() as local_dir:
            local_paths = mcap_scene_update_export.write_annotation_files(
                session=self._session,
                sequence_ids=sequence_ids,
                annotation_collection_id=annotation_collection.collection_id,
                target_frame_id=target_frame_id,
                local_dir=Path(local_dir),
                topic=topic,
                suffix=suffix,
            )
            return mcap_scene_update_export.upload(local_paths=local_paths, output_dir=output_dir)

    def get_sequences(self) -> list[McapSequence]:
        """Get the sequences of the dataset, one per recording that was indexed.

        Returns:
            The sequences, ordered by the time they were created at.
        """
        views = mcap_group_sequence_resolver.get_all_by_collection_id(
            session=self._session, collection_id=self.collection_id, pagination=None
        )
        return [
            McapSequence(
                session=self._session,
                sample_id=view.sample_id,
                recording_id=view.recording_id,
            )
            for view in views.samples
        ]

    def get_recording(self, recording_id: UUID) -> Recording:
        """Get one recording of the dataset by its ID.

        Args:
            recording_id: The ID of the recording, e.g. `sequence.recording_id`.

        Returns:
            The recording.

        Raises:
            ValueError: If no recording of that ID exists.
        """
        recording = recording_resolver.get_by_id(session=self._session, recording_id=recording_id)
        if recording is None:
            raise ValueError(f"Recording with id {recording_id} not found.")
        return Recording(session=self._session, inner=recording)

    def create_recording(
        self, uri: str, recording_format: RecordingFormat = RecordingFormat.MCAP
    ) -> Recording:
        """Add a recording to the dataset.

        Create the recording before its groups, so that its calibration can be stored
        before anything refers to it.

        Args:
            uri: Where the bytes of the recording are, e.g. `/data/perception.mcap` or
                `s3://my-bucket/perception.mcap`.
            recording_format: The format of the recording.

        Returns:
            The created recording.

        Raises:
            ValueError: If `uri` is empty or only whitespace.
        """
        recording_id = recording_resolver.create(
            session=self._session,
            dataset_id=self.dataset_id,
            uri=uri,
            format_=recording_format,
        )
        recording = recording_resolver.get_by_id(session=self._session, recording_id=recording_id)
        if recording is None:
            raise RuntimeError("Failed to retrieve the created recording.")
        return Recording(session=self._session, inner=recording)

    def create_sequence(self, recording_id: UUID) -> McapSequence:
        """Add a sequence that orders the groups of one recording.

        Args:
            recording_id: The ID of the recording the groups are indexed from.

        Returns:
            The created sequence.

        Raises:
            ValueError: If no recording of that ID exists.
        """
        sample_id = mcap_group_sequence_resolver.create(
            session=self._session,
            collection_id=self.collection_id,
            recording_id=recording_id,
        )
        return McapSequence(session=self._session, sample_id=sample_id, recording_id=recording_id)

    def _group_collection(self) -> CollectionTable:
        """Return the GROUP child collection holding the groups of the dataset.

        Raises:
            RuntimeError: If the dataset has no GROUP child collection.
        """
        for child in self._inner.children:
            if child.sample_type == SampleType.GROUP:
                return child
        raise RuntimeError(
            f"Dataset '{self.name}' has no group collection. It was not created with "
            "`McapDataset.create`."
        )

    def _annotation_collection(self, annotation_source: str) -> CollectionTable:
        """Return the annotation set of that source name.

        Raises:
            ValueError: If the dataset has no annotation source of that name.
        """
        collections = collection_resolver.get_annotation_collections(
            session=self._session, parent_collection_id=self.group_dataset.collection_id
        )
        for collection in collections:
            if collection.name == annotation_source:
                return collection
        available = _format_names(names=sorted(collection.name for collection in collections))
        raise ValueError(
            f"Annotation source '{annotation_source}' not found. Available: {available}."
        )

    def _default_target_frame_id(self, sequence_ids: Sequence[UUID]) -> str:
        """Return the first frame of `export_frame_ids` for the sequences.

        That is the frame most cuboids are stored in or, without cuboids, the first
        reference frame that the recordings of the sequences share.

        Raises:
            ExportError: If the recordings share no coordinate frame.
        """
        frame_ids = mcap_scene_update_export.export_frame_ids(
            session=self._session, sequence_ids=sequence_ids
        )
        if not frame_ids:
            raise ExportError(
                "The recordings share no coordinate frame. Pass `target_frame_id` explicitly."
            )
        return frame_ids[0]


def _recording_paths(discovered_paths: Iterable[str], limit: int | None) -> list[str]:
    """Filter annotation MCAPs before lazily applying the recording limit."""
    recordings = (
        path for path in discovered_paths if not annotation_mcap.is_annotation_mcap(uri=path)
    )
    return list(recordings if limit is None else islice(recordings, limit))


def _get_duplicate_names(components: Sequence[McapComponentSpec]) -> list[str]:
    """Return the names that more than one component uses, in the order they appear."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for component in components:
        if component.name in seen and component.name not in duplicates:
            duplicates.append(component.name)
        seen.add(component.name)
    return duplicates


def _format_names(names: Sequence[str]) -> str:
    """Format names as quoted, comma separated items for an error message."""
    return ", ".join(f"'{name}'" for name in names)
