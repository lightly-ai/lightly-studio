<script lang="ts">
    import { useGroupComponents } from '$lib/hooks/useGroupComponents/useGroupComponents';
    import { SampleType, type GroupComponentView } from '$lib/api/lightly_studio_local';
    import { GroupComponents } from '$lib/components/GroupComponents';
    import * as utils from '$lib/utils';
    import GroupComponent from '$lib/components/GroupComponent/GroupComponent.svelte';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';

    const {
        groupId,
        componentId,
        datasetId,
        collectionId
    }: {
        groupId: string;
        componentId: string;
        datasetId: string;
        collectionId: string;
    } = $props();

    const { groupComponents } = useGroupComponents({ groupId });
    const components = $derived<GroupComponentView[]>($groupComponents.data ?? []);
    let selectedComponentId = $state(componentId);
    const selectedIndex = $derived(
        components.findIndex((c) => c.details?.sample_id === selectedComponentId)
    );

    /**
     * Navigate to the component details page for a given component ID.
     */
    const navigateToComponentDetails = (componentId: string, type: SampleType) => {
        if (type === 'image') {
            goto(
                routeHelpers.toSample({
                    datasetId,
                    collectionType: 'group',
                    collectionId,
                    sampleId: componentId,
                    groupId
                }),
                { invalidateAll: true }
            );
        } else if (type === 'video') {
            goto(
                routeHelpers.toVideosDetails({
                    datasetId,
                    collectionType: 'group',
                    collectionId,
                    sampleId: componentId,
                    groupId
                }),
                { invalidateAll: true }
            );
        } else {
            throw new Error('Unknown component type');
        }
    };
    const handleClick = (index: number) => {
        const component = components[index];
        const compId = component.details?.sample_id;
        const componentType = component.details?.type ?? undefined;
        if (!compId) {
            throw new Error('Component ID is missing for the selected component');
        }
        if (!componentType) {
            throw new Error('Component type is missing for the selected component');
        }
        selectedComponentId = compId;
        navigateToComponentDetails(compId, componentType);
    };
</script>

<GroupComponents itemsCount={components.length} {selectedIndex} onclick={handleClick}>
    {#snippet renderItem({ index })}
        {@const component = components[index]}

        {#if !component.details}
            <div class="flex h-60 w-60 items-center justify-center rounded bg-gray-700">
                No details
            </div>
        {:else}
            <GroupComponent
                src={utils.isImageView(component.details)
                    ? utils.getImageURLById(component.details.sample_id)
                    : utils.getVideoURLById(component.details.sample_id)}
                type={utils.isImageView(component.details) ? 'image' : 'video'}
                title={component.collection.group_component_name}
            />
        {/if}
    {/snippet}
</GroupComponents>
