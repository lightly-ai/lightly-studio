<script lang="ts">
    import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import Spinner from '$lib/components/Spinner/Spinner.svelte';
    import { LazyTrigger } from '$lib/components/LazyTrigger';
    import { Grid } from '../Grid';
    import GridItem from '../GridItem/GridItem.svelte';

    let {
        collectionId,
        groups,
        isLoading,
        isEmpty,
        hasNextPage,
        isFetchingNextPage,
        onLoadMore
    }: {
        collectionId: string;
        groups: GroupView[];
        isLoading: boolean;
        isEmpty: boolean;
        hasNextPage: boolean;
        isFetchingNextPage: boolean;
        onLoadMore: () => void;
    } = $props();

    const GRID_GAP = 16;

    const { sampleSize, getSelectedSampleIds, toggleSampleSelection } = useGlobalStorage();

    const selectedSampleIds = $derived(getSelectedSampleIds(collectionId));

    let viewport: HTMLElement | null = $state(null);
    let clientWidth = $state(0);
    let clientHeight = $state(0);

    const columnCount = $derived($sampleSize.width);
    const itemSize = $derived.by(() => {
        if (clientWidth === 0) return 0;
        return clientWidth / columnCount;
    });
    const sampleItemSize = $derived(itemSize - GRID_GAP);

    function handleClick(sampleId: string) {
        return (event: MouseEvent) => {
            event.preventDefault();
            toggleSampleSelection(sampleId, collectionId);
        };
    }

    function handleKeyDown(sampleId: string) {
        return (event: KeyboardEvent) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                toggleSampleSelection(sampleId, collectionId);
            }
        };
    }
</script>

{#if isLoading}
    <div class="flex h-full w-full items-center justify-center">
        <Spinner />
        <div>Loading groups...</div>
    </div>
{:else if isEmpty}
    <div class="flex h-full w-full items-center justify-center">
        <div class="text-center text-muted-foreground">
            <div class="mb-2 text-lg font-medium">No groups found</div>
            <div class="text-sm">This collection doesn't contain any groups.</div>
        </div>
    </div>
{:else}
    <Grid itemCount={groups.length} {columnCount}>
        {#snippet gridItem({ index, style, width, height })}
            <GridItem {width} {height} containerProps={{ style }}>
                <img
                    src="https://picsum.photos/150?random={index + 200}"
                    alt="Placeholder {index + 1}"
                    class="h-full w-full object-cover"
                />
            </GridItem>
        {/snippet}
        {#snippet footerItem()}
            {#key groups.length}
                <LazyTrigger
                    onIntersect={onLoadMore}
                    disabled={!hasNextPage || isFetchingNextPage}
                />
            {/key}
            {#if isFetchingNextPage}
                <div class="flex justify-center p-4">
                    <Spinner />
                </div>
            {/if}
        {/snippet}
    </Grid>
{/if}
