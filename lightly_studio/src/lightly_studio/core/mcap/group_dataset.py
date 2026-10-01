"""The group child dataset of an MCAP dataset."""

from __future__ import annotations

from lightly_studio.core.group.group_dataset import GroupDataset
from lightly_studio.core.mcap.component import McapComponent
from lightly_studio.resolvers import collection_resolver


class McapGroupDataset(GroupDataset):
    """The groups of an MCAP dataset, one group per synchronized tick of a recording.

    It adds access to the components of the groups on top of `GroupDataset`:

    ```python
    front = group_dataset.get_component("front")

    group_sample = group_dataset.add_group_sample(
        components={
            "front": ls.CreateMcap.from_frame_locator(locator=frame),
            "pcl_front": ls.CreateMcap.from_frame_locator(locator=sweep),
        }
    )
    ```
    """

    def get_component(self, name: str) -> McapComponent:
        """Get one component of the groups by its name.

        Args:
            name: The name of the component, as given to `McapDataset.create`.

        Returns:
            The component.

        Raises:
            KeyError: If the dataset has no component of that name.
        """
        components = collection_resolver.get_group_components(
            session=self.session, parent_collection_id=self.collection_id
        )
        if name not in components:
            known_names = ", ".join(sorted(components)) or "none"
            raise KeyError(
                f"Component '{name}' is not in the dataset. Known components: {known_names}."
            )
        return McapComponent(
            session=self.session,
            collection_id=components[name].collection_id,
            name=name,
        )
