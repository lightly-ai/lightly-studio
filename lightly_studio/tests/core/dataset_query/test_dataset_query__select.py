from __future__ import annotations

from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.resolvers import collection_resolver, tag_resolver
from tests import helpers_resolvers


class TestDatasetQuerySelect:
    def test_selection_creates_tag_for_selected_samples(self, db_session: Session) -> None:
        """Integration: running selection tags selected samples."""
        root_collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            session=db_session,
            n_samples=5,
            embedding_model_names=["embedding_model_1"],
        )
        dataset_table = collection_resolver.get_by_id(
            session=db_session, collection_id=root_collection_id
        )
        assert dataset_table is not None
        query = DatasetQuery(dataset=dataset_table, session=db_session)

        query.selection().diverse(
            n_samples_to_select=2,
            selection_result_tag_name="selection_tag",
        )

        tag = tag_resolver.get_by_name(
            session=db_session, tag_name="selection_tag", collection_id=root_collection_id
        )
        assert tag is not None, "Selection tag should be created"

        samples_in_tag = query.match(ImageSampleField.tags.contains("selection_tag")).to_list()
        assert len(samples_in_tag) == 2
