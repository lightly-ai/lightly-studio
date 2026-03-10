<script lang="ts">
    /**
     * Redirect page for group detail view.
     *
     * This page automatically redirects to the first component's detail page within a group.
     * When a user navigates to /groups/[sampleId], they are immediately redirected to
     * /groups/[sampleId]/[componentId] where componentId is the sample_id of the first
     * component in the group.
     */
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import type { GroupComponentView } from '$lib/api/lightly_studio_local';
    import { useGroupComponents } from '$lib/hooks/useGroupComponents/useGroupComponents';
    import { routeHelpers } from '$lib/routes';

    const groupId = page.params.sampleId;
    const datasetId = page.params.dataset_id!;
    const collectionType = page.params.collection_type!;
    const collectionId = page.params.collection_id!;

    // Fetch all components for this group
    const { groupComponents } = useGroupComponents({ groupId });
    const components = $derived<GroupComponentView[]>($groupComponents.data ?? []);

    // Extract the sample_id of the first component to redirect to
    const firstComponentId = $derived(
        components.length > 0 ? components[0].details?.sample_id : null
    );

    /**
     * Navigate to the component details page for a given component ID.
     */
    const navigateToComponentDetails = (componentId: string) => {
        goto(
            routeHelpers.toGroupComponentDetails(
                datasetId,
                collectionType,
                collectionId,
                groupId,
                componentId
            )
        );
    };

    // Automatically redirect to the first component when it becomes available
    $effect(() => {
        if (firstComponentId) {
            navigateToComponentDetails(firstComponentId);
        }
    });
</script>
