"""Handler for database operations related to samples."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.sample import SampleTable

# def create(session: Session, sample: ImageCreate) -> ImageTable:
#     """Create a new sample in the database."""
#     # TODO(Michal, 10/2025): Temporarily create sample table entry here until
#     # ImageTable and SampleTable are properly split.
#     db_sample = SampleTable()
#     session.add(db_sample)
#     session.commit()

#     # Use the helper class to provide sample_id.
#     db_image = ImageTable.model_validate(
#         ImageCreateHelper(
#             file_name=sample.file_name,
#             width=sample.width,
#             height=sample.height,
#             dataset_id=sample.dataset_id,
#             file_path_abs=sample.file_path_abs,
#             sample_id=db_sample.sample_id,
#         )
#     )
#     session.add(db_image)
#     session.commit()
#     session.refresh(db_image)
#     return db_image


# def create_many(session: Session, samples: list[ImageCreate]) -> list[ImageTable]:
#     """Create multiple samples in a single database commit."""
#     # TODO(Michal, 10/2025): Temporarily create sample table entry here until
#     # ImageTable and SampleTable are properly split.
#     # Note: We are using bulk insert for SampleTable to get sample_ids efficiently.
#     statement = (
#         insert(SampleTable).values([{} for _ in samples]).returning(col(SampleTable.sample_id))
#     )
#     sample_ids: ScalarResult[UUID] = session.execute(statement).scalars()

#     # Bulk create ImageTable entries using the generated sample_ids.
#     db_images = [
#         ImageTable.model_validate(
#             ImageCreateHelper(
#                 file_name=sample.file_name,
#                 width=sample.width,
#                 height=sample.height,
#                 dataset_id=sample.dataset_id,
#                 file_path_abs=sample.file_path_abs,
#                 sample_id=sample_id,
#             )
#         )
#         for sample_id, sample in zip(sample_ids, samples)
#     ]
#     session.bulk_save_objects(db_images)
#     session.commit()
#     return db_images


def get_by_id(session: Session, sample_id: UUID) -> SampleTable | None:
    """Retrieve a single sample by ID."""
    return session.exec(select(SampleTable).where(SampleTable.sample_id == sample_id)).one_or_none()


# def get_many_by_id(session: Session, sample_ids: list[UUID]) -> list[ImageTable]:
#     """Retrieve multiple samples by their IDs.

#     Output order matches the input order.
#     """
#     results = session.exec(
#         select(ImageTable).where(col(ImageTable.sample_id).in_(sample_ids))
#     ).all()
#     # Return samples in the same order as the input IDs
#     sample_map = {sample.sample_id: sample for sample in results}
#     return [sample_map[id_] for id_ in sample_ids if id_ in sample_map]
