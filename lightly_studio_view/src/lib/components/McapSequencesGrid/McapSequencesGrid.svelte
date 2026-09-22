<script lang="ts">
    import { Grid } from '$lib/components/Grid';
    import { GridContainer } from '$lib/components/GridContainer';
    import { GridItem } from '$lib/components/GridItem';
    import { McapSequenceGridItem } from '$lib/components/McapSequenceGridItem';
    import { useGlobalStorage } from '$lib/hooks';
    import type { McapSequenceFrame } from '$lib/api/lightly_studio_local/types.gen';

    interface McapSequence {
        sampleId: string;
        sampleCount: number;
        sequenceFrame: McapSequenceFrame | null | undefined;
    }

    interface Props {
        sequences: McapSequence[];
        isLoading: boolean;
        isEmpty: boolean;
        isError: boolean;
        hasNextPage: boolean;
        isFetchingNextPage: boolean;
        onLoadMore: () => void;
        onSequenceClick: (sampleId: string) => void;
    }

    let {
        sequences,
        isLoading,
        isEmpty,
        isError,
        hasNextPage,
        isFetchingNextPage,
        onLoadMore,
        onSequenceClick
    }: Props = $props();

    const { sampleSize } = useGlobalStorage();
    const columnCount = $derived($sampleSize.width);
</script>

<div class="h-full w-full">
    <GridContainer
        itemCount={sequences.length}
        message={{
            loading: 'Loading sequences...',
            empty: {
                title: 'No sequences found',
                description: "This collection doesn't contain any MCAP sequences."
            }
        }}
        status={{
            loading: isLoading,
            error: isError,
            empty: isEmpty,
            success: !isLoading && !isEmpty && !isError
        }}
        loader={{
            loadMore: onLoadMore,
            disabled: !hasNextPage || isFetchingNextPage,
            loading: isFetchingNextPage
        }}
    >
        {#snippet children({ footer })}
            <Grid
                itemCount={sequences.length}
                {columnCount}
                viewportProps={{ 'data-testid': 'mcap-sequences-grid-viewport' }}
                gridProps={{
                    'data-testid': 'mcap-sequences-grid',
                    class: 'dark:[color-scheme:dark]'
                }}
            >
                {#snippet gridItem({ index, style, width, height })}
                    {#if sequences[index]}
                        <GridItem
                            {width}
                            {height}
                            {style}
                            dataTestId={`mcap-sequence-grid-item-button-${sequences[index].sampleId}`}
                            tag={false}
                            onSelect={() => onSequenceClick(sequences[index].sampleId)}
                            ariaLabel={`View MCAP sequence ${index + 1}`}
                        >
                            <McapSequenceGridItem
                                sampleCount={sequences[index].sampleCount}
                                sequenceFrame={sequences[index].sequenceFrame}
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
