import pytest

from lightly_studio import db_manager
from lightly_studio.core.group_dataset import GroupDataset
from lightly_studio.core.group_sample import GroupSample
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection


class TestGroupDataset:
    def test_create(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        group_ds = GroupDataset.create(
            components=[
                ("img", SampleType.IMAGE),
                ("vid", SampleType.VIDEO),
            ],
            name="test_group_dataset",
        )
        dataset_id = group_ds.dataset_id

        assert group_ds.sample_type() == SampleType.GROUP
        assert group_ds.sample_class() == GroupSample

        session = group_ds.session
        component_cols = collection_resolver.get_group_components(
            session=session, parent_collection_id=dataset_id
        )
        assert len(component_cols) == 2
        assert component_cols["img"].sample_type == SampleType.IMAGE
        assert component_cols["vid"].sample_type == SampleType.VIDEO

    def test_load(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        session = db_manager.persistent_session()
        group_col = create_collection(
            session=session, sample_type=SampleType.GROUP, collection_name="test_group_dataset"
        )

        group_ds = GroupDataset.load(name="test_group_dataset")

        assert group_ds.dataset_id == group_col.collection_id
        assert group_ds.name == "test_group_dataset"

    def test_load_or_create(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        # First call creates the dataset
        group_ds_1 = GroupDataset.load_or_create(components=[("img", SampleType.IMAGE)])

        # Second call loads the existing dataset
        group_ds_2 = GroupDataset.load_or_create(components=[("img", SampleType.IMAGE)])
        assert group_ds_1.dataset_id == group_ds_2.dataset_id

        # Mismatched schema raises ValueError
        with pytest.raises(
            ValueError, match=r"already exists with a different number of components \(1 vs 2\)."
        ):
            GroupDataset.load_or_create(
                components=[("img", SampleType.IMAGE), ("extra", SampleType.IMAGE)]
            )
        with pytest.raises(
            ValueError, match=r"Key 'vid' with type 'image' not found in existing dataset."
        ):
            GroupDataset.load_or_create(components=[("vid", SampleType.IMAGE)])
        with pytest.raises(
            ValueError, match=r"Key 'img' with type 'video' not found in existing dataset."
        ):
            GroupDataset.load_or_create(components=[("img", SampleType.VIDEO)])
