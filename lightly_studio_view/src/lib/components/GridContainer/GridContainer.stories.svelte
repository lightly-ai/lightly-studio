<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import GridContainer from './GridContainer.svelte';
    import Grid from '../Grid/Grid.svelte';
    import GridItem from '../GridItem/GridItem.svelte';

    const { Story } = defineMeta({
        title: 'Components/GridContainer',
        tags: ['autodocs']
    });

    const itemCount = 60;
    const message = {
        loading: 'Loading samples...',
        error: 'Failed to load samples.',
        empty: {
            title: 'No samples found',
            description: 'Try adjusting your filters to see more content.'
        }
    };
</script>

<Story name="Loading" asChild>
    <div class="h-[480px] w-full">
        <GridContainer
            status={{ loading: true, error: false, empty: false, success: false }}
            {message}
        />
    </div>
</Story>

<Story name="Error" asChild>
    <div class="h-[480px] w-full">
        <GridContainer
            status={{ loading: false, error: true, empty: false, success: false }}
            {message}
        />
    </div>
</Story>

<Story name="Empty" asChild>
    <div class="h-[480px] w-full">
        <GridContainer
            status={{ loading: false, error: false, empty: true, success: false }}
            {message}
        />
    </div>
</Story>

<Story name="Success" asChild>
    <div class="h-[480px] w-full">
        <GridContainer
            status={{ loading: false, error: false, empty: false, success: true }}
            {message}
            loader={{ loadMore: () => undefined, disabled: false, loading: false }}
            {itemCount}
        >
            {#snippet children({ footer })}
                <Grid {itemCount} columnCount={6}>
                    {#snippet gridItem({ index, style, width, height })}
                        <GridItem {width} {height} {style} caption={`sample-${index + 1}.jpg`}>
                            <img
                                src="https://picsum.photos/180?random={index}"
                                alt="Sample {index + 1}"
                                class="h-full w-full object-cover"
                            />
                        </GridItem>
                    {/snippet}

                    {#snippet footerItem()}
                        {@render footer()}
                    {/snippet}
                </Grid>
            {/snippet}
        </GridContainer>
    </div>
</Story>

<Story name="Success - Fetching Next Page" asChild>
    <div class="h-[480px] w-full">
        <GridContainer
            status={{ loading: false, error: false, empty: false, success: true }}
            {message}
            loader={{ loadMore: () => undefined, disabled: true, loading: true }}
            {itemCount}
        >
            {#snippet children({ footer })}
                <Grid {itemCount} columnCount={6}>
                    {#snippet gridItem({ index, style, width, height })}
                        <GridItem {width} {height} {style} caption={`sample-${index + 1}.jpg`}>
                            <img
                                src="https://picsum.photos/180?random={index + 500}"
                                alt="Sample {index + 1}"
                                class="h-full w-full object-cover"
                            />
                        </GridItem>
                    {/snippet}

                    {#snippet footerItem()}
                        {@render footer()}
                    {/snippet}
                </Grid>
            {/snippet}
        </GridContainer>
    </div>
</Story>
