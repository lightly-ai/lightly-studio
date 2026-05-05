<script lang="ts">
    import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { Grid } from '../Grid';
    import { GridItem } from '../GridItem';
    import { GridContainer } from '../GridContainer';
    import { GroupGridItem } from '../GroupGridItem';

    let {
        groups,
        isLoading,
        isEmpty,
        hasNextPage,
        isFetchingNextPage,
        onLoadMore,
        navigateToSampleDetailsByView
    }: {
        groups: GroupView[];
        isLoading: boolean;
        isEmpty: boolean;
        hasNextPage: boolean;
        isFetchingNextPage: boolean;
        onLoadMore: () => void;
        navigateToSampleDetailsByView: (view: GroupView) => void;
    } = $props();

    const { sampleSize } = useGlobalStorage();
    const columnCount = $derived($sampleSize.width);

    const handleDblClick = (view: GroupView) => {
        if (!view) {
            throw new Error('View is missing for the selected group');
        }
        // For videos, we want to navigate to the group details page on double click
        navigateToSampleDetailsByView(view);
    };
</script>

<div class="h-full w-full">
    <GridContainer
        itemCount={groups.length}
        message={{
            loading: 'Loading groups...',
            empty: {
                title: 'No groups found',
                description: "This collection doesn't contain any groups."
            }
        }}
        status={{
            loading: isLoading,
            error: false,
            empty: isEmpty,
            success: !isLoading && !isEmpty
        }}
        loader={{
            loadMore: onLoadMore,
            disabled: !hasNextPage || isFetchingNextPage,
            loading: isFetchingNextPage
        }}
    >
        {#snippet children({ footer })}
            <Grid
                itemCount={groups.length}
                {columnCount}
                viewportProps={{ 'data-testid': 'groups-grid-viewport' }}
                gridProps={{ 'data-testid': 'groups-grid', class: 'dark:[color-scheme:dark]' }}
            >
                {#snippet gridItem({ index, style, width, height })}
                    {#if groups[index]}
                        <GridItem
                            {width}
                            {height}
                            {style}
                            dataTestId={`group-grid-item-button-${groups[index].sample_id}`}
                            tag={false}
                            ondblclick={() => handleDblClick(groups[index])}
                            ariaLabel={`View group ${index + 1}`}
                        >
                            <GroupGridItem
                                sample={groups[index].group_preview}
                                sample_count={groups[index].sample_count}
                                {width}
                                {height}
                            />
                        </GridItem>
                    {/if}
                {/snippet}
                {#snippet footerItem()}
                    {@render footer()}
                {/snippet}
            </Grid>
        {/snippet}
    </GridContainer>
</div>
