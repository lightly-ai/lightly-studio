<script lang="ts">
    import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import Spinner from '$lib/components/Spinner/Spinner.svelte';
    import { LazyTrigger } from '$lib/components/LazyTrigger';
    import { Grid } from '../Grid';
    import GridItem from '../GridItem/GridItem.svelte';
    import GroupItem from '../GroupItem/GroupItem.svelte';

    let {
        groups,
        isLoading,
        isEmpty,
        hasNextPage,
        isFetchingNextPage,
        onLoadMore
    }: {
        groups: GroupView[];
        isLoading: boolean;
        isEmpty: boolean;
        hasNextPage: boolean;
        isFetchingNextPage: boolean;
        onLoadMore: () => void;
    } = $props();

    const { sampleSize } = useGlobalStorage();
    const columnCount = $derived($sampleSize.width);

    let clientWidth = $state(0);
</script>

<div class="h-full w-full" bind:clientWidth>
    {#if isLoading}
        <div class="flex h-full w-full items-center justify-center">
            <Spinner />
            <div class="ml-2">Loading groups...</div>
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
                    <GroupItem
                        sample={groups[index].group_preview}
                        sample_count={groups[index].sample_count}
                        {width}
                        {height}
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
</div>
