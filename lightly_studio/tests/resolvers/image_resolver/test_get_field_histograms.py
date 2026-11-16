from sqlmodel import Session

from lightly_studio.models.metadata import HistogramView
from lightly_studio.resolvers import image_resolver, tag_resolver
from lightly_studio.resolvers.image_filter import FilterDimensions, ImageFilter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import ImageStub, create_collection, create_images, create_tag


def test_get_field_histograms(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="a.jpg", width=100, height=10),
            ImageStub(path="b.jpg", width=150, height=20),
            ImageStub(path="c.jpg", width=300, height=30),
        ],
    )

    histograms = image_resolver.get_field_histograms(
        session=db_session, collection_id=collection_id, bin_count=2
    )

    assert histograms == {
        "width": HistogramView(bin_edges=[100.0, 200.0, 300.0], counts=[2, 1]),
        "height": HistogramView(bin_edges=[10.0, 20.0, 30.0], counts=[1, 2]),
    }


def test_get_field_histograms__fields(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path="a.jpg", width=100, height=10)],
    )

    histograms = image_resolver.get_field_histograms(
        session=db_session, collection_id=collection_id, fields=["height"]
    )

    assert list(histograms) == ["height"]


def test_get_field_histograms__single_value(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="a.jpg", width=100, height=10),
            ImageStub(path="b.jpg", width=100, height=10),
        ],
    )

    histograms = image_resolver.get_field_histograms(
        session=db_session, collection_id=collection_id, fields=["width"]
    )

    assert histograms == {"width": HistogramView(bin_edges=[100.0, 100.0], counts=[2])}


def test_get_field_histograms__no_images(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id

    histograms = image_resolver.get_field_histograms(
        session=db_session, collection_id=collection_id
    )

    assert histograms == {}


def test_get_field_histograms__other_collection_is_ignored(db_session: Session) -> None:
    collection_id = create_collection(session=db_session, collection_name="a").collection_id
    other_collection_id = create_collection(session=db_session, collection_name="b").collection_id
    create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path="a.jpg", width=100, height=10)],
    )
    create_images(
        db_session=db_session,
        collection_id=other_collection_id,
        images=[ImageStub(path="b.jpg", width=900, height=90)],
    )

    histograms = image_resolver.get_field_histograms(
        session=db_session, collection_id=collection_id, fields=["width"]
    )

    assert histograms == {"width": HistogramView(bin_edges=[100.0, 100.0], counts=[1])}


def test_get_field_histograms__filters_are_faceted(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="a.jpg", width=100, height=10),
            ImageStub(path="b.jpg", width=150, height=20),
            ImageStub(path="c.jpg", width=300, height=30),
        ],
    )
    filters = ImageFilter(
        width=FilterDimensions(min=100, max=150),
        height=FilterDimensions(min=20, max=30),
    )

    histograms = image_resolver.get_field_histograms(
        session=db_session, collection_id=collection_id, filters=filters, bin_count=2
    )

    # The width histogram ignores the width filter and applies the height filter: b.jpg, c.jpg.
    # The height histogram ignores the height filter and applies the width filter: a.jpg, b.jpg.
    assert histograms == {
        "width": HistogramView(bin_edges=[100.0, 200.0, 300.0], counts=[1, 1]),
        "height": HistogramView(bin_edges=[10.0, 20.0, 30.0], counts=[1, 1]),
    }


def test_get_field_histograms__single_value_with_filter(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="a.jpg", width=100, height=10),
            ImageStub(path="b.jpg", width=100, height=20),
        ],
    )

    histograms = image_resolver.get_field_histograms(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(height=FilterDimensions(min=20, max=20)),
        fields=["width"],
    )

    assert histograms == {"width": HistogramView(bin_edges=[100.0, 100.0], counts=[1])}


def test_get_field_histograms__tag_filter(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="a.jpg", width=100, height=10),
            ImageStub(path="b.jpg", width=300, height=30),
        ],
    )
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="big")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[images[1].sample_id]
    )

    histograms = image_resolver.get_field_histograms(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tag.tag_id])),
        bin_count=2,
        fields=["width"],
    )

    assert histograms == {
        "width": HistogramView(bin_edges=[100.0, 200.0, 300.0], counts=[0, 1]),
    }


def test_get_field_histograms__metadata_key_named_width(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="a.jpg", width=100, height=10),
            ImageStub(path="b.jpg", width=300, height=30),
        ],
    )
    images[0].sample["width"] = 5000
    images[1].sample["width"] = 7

    # A metadata filter on the "width" key is not the image width filter, so it still applies.
    histograms = image_resolver.get_field_histograms(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                metadata_filters=[MetadataFilter(key="width", op=">=", value=1000)]
            )
        ),
        bin_count=2,
        fields=["width"],
    )

    assert histograms == {
        "width": HistogramView(bin_edges=[100.0, 200.0, 300.0], counts=[1, 0]),
    }
