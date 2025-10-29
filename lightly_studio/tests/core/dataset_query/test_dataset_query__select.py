from __future__ import annotations

from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.sample_field import SampleField
from lightly_studio.resolvers import datasets_resolver, tag_resolver
from tests import helpers_resolvers


class TestDatasetQuerySelect:
    def test_selection_creates_tag_for_selected_samples(self, test_db: Session) -> None:
        """Integration: running selection tags selected samples."""
        dataset_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            test_db=test_db,
            n_samples=5,
            embedding_model_names=["embedding_model_1"],
        )
        dataset_table = datasets_resolver.get_by_id(test_db, dataset_id)
        assert dataset_table is not None
        query = DatasetQuery(dataset=dataset_table, session=test_db)

        query.selection().diverse(
            n_samples_to_select=2,
            selection_result_tag_name="selection_tag",
        )

        tag = tag_resolver.get_by_name(
            session=test_db, tag_name="selection_tag", dataset_id=dataset_id
        )
        assert tag is not None, "Selection tag should be created"

        samples_in_tag = query.match(SampleField.tags.contains("selection_tag")).to_list()
        assert len(samples_in_tag) == 2
