from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image


def _splits(*sizes_by_name: tuple[str, int]) -> list[tag_resolver.SplitDefinition]:
    return [
        tag_resolver.SplitDefinition(tag_name=name, relative_size=size)
        for name, size in sizes_by_name
    ]


def _create_sample_ids(session: Session, collection_id: UUID, count: int) -> list[UUID]:
    return [
        create_image(
            session=session, collection_id=collection_id, file_path_abs=f"s{index}.png"
        ).sample_id
        for index in range(count)
    ]


def test_split_samples__partitions_by_relative_size(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    sample_ids = _create_sample_ids(session=db_session, collection_id=collection_id, count=9)

    # 7/2/1 over 9 samples has exact quotients 6/1/0, so the two largest remainders ("test"
    # with 0.9 and "val" with 0.8) each take one leftover sample. The repeated ID must not take
    # a slot, which makes the counts prove deduplication too.
    counts = tag_resolver.split_samples(
        session=db_session,
        collection_id=collection_id,
        sample_ids=sample_ids + sample_ids[:1],
        splits=_splits(("train", 7), ("val", 2), ("test", 1)),
        seed=4,
    )

    assert counts == {"train": 6, "val": 2, "test": 1}
    # Equality as a multiset proves every sample is tagged exactly once.
    tagged_sample_ids = [
        sample_id
        for tag in tag_resolver.get_all_by_collection_id(
            session=db_session, collection_id=collection_id
        )
        for sample_id in tag_resolver.get_sample_ids_by_tag_id(
            session=db_session, tag_id=tag.tag_id
        )
    ]
    assert sorted(tagged_sample_ids) == sorted(sample_ids)
