<script lang="ts">
    import { page } from '$app/state';
    import { createSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { ImageDetails } from '$lib/components';
    import GroupsComponentsMenu from '$lib/components/GroupsComponentsMenu/GroupsComponentsMenu.svelte';
    import LayoutCard from '$lib/components/LayoutCard/LayoutCard.svelte';

    const { children } = $props();

    createSampleDetailsToolbarContext();

    const sampleId = $derived(page.params.sampleId);
    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type);
    const collection = page.data.collection;
    const collectionId = $derived(page.params.collection_id!);

    const groupId = $derived.by(() => {
        return page.url.searchParams.get('group_id') ?? undefined;
    });
</script>

{#if collectionType === 'group' && groupId}
    <div class="flex h-full gap-4 px-4 pb-4">
        <div class="flex-none">
            <LayoutCard className="p-4 max-h-full overflow-y-auto dark:[color-scheme:dark]">
                <GroupsComponentsMenu {groupId} componentId={sampleId} {datasetId} {collectionId} />
            </LayoutCard>
        </div>

        <div class="grow">
            <LayoutCard className="p-4">
                <ImageDetails {sampleId} {collection}>
                    {#if children}
                        {@render children()}
                    {/if}
                </ImageDetails>
            </LayoutCard>
        </div>
    </div>
{:else}
    <div class="flex h-full w-full space-x-4 px-4 pb-4" data-testid="sample-details">
        <div class="h-full w-full space-y-6 rounded-[1vw] bg-card p-4">
            <ImageDetails {sampleId} {collection}>
                {#if children}
                    {@render children()}
                {/if}
            </ImageDetails>
        </div>
    </div>
{/if}
