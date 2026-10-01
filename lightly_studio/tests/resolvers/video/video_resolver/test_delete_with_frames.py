from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers import video_resolver
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_sample_embedding,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_delete_with_frames(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    deleted_video = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="deleted.mp4", duration_s=2, fps=1),
    )
    retained_video = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="retained.mp4", duration_s=2, fps=1),
    )
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=deleted_video.video_frames_collection_id,
        embedding_dimension=2,
    )
    deleted_sample_ids = [deleted_video.video_sample_id, *deleted_video.frame_sample_ids]
    retained_sample_ids = [retained_video.video_sample_id, *retained_video.frame_sample_ids]
    for sample_id in [*deleted_video.frame_sample_ids, *retained_video.frame_sample_ids]:
        create_sample_embedding(
            session=db_session,
            sample_id=sample_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding=[1.0, 2.0],
        )

    video_resolver.delete_with_frames(
        session=db_session, video_sample_id=deleted_video.video_sample_id
    )

    assert db_session.get(VideoTable, deleted_video.video_sample_id) is None
    for frame_sample_id in deleted_video.frame_sample_ids:
        assert db_session.get(VideoFrameTable, frame_sample_id) is None
    for sample_id in deleted_sample_ids:
        assert db_session.get(SampleTable, sample_id) is None
    for frame_sample_id in deleted_video.frame_sample_ids:
        assert (
            db_session.get(
                SampleEmbeddingTable,
                (frame_sample_id, embedding_model.embedding_model_id),
            )
            is None
        )

    assert db_session.get(VideoTable, retained_video.video_sample_id) is not None
    for frame_sample_id in retained_video.frame_sample_ids:
        assert db_session.get(VideoFrameTable, frame_sample_id) is not None
    for sample_id in retained_sample_ids:
        assert db_session.get(SampleTable, sample_id) is not None
    for frame_sample_id in retained_video.frame_sample_ids:
        assert (
            db_session.get(
                SampleEmbeddingTable,
                (frame_sample_id, embedding_model.embedding_model_id),
            )
            is not None
        )
