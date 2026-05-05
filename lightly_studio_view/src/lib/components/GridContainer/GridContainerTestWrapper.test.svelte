<script lang="ts">
    import GridContainer from './GridContainer.svelte';

    let {
        status = { loading: false, error: false, empty: false, success: true },
        message = {
            loading: 'Loading samples...',
            error: 'Failed to load samples.',
            empty: {
                title: 'No samples found',
                description: 'Try adjusting your filters.'
            }
        },
        itemCount = 12,
        loaderDisabled = false,
        loaderLoading = false,
        onLoadMore = () => undefined
    }: {
        status?: { loading: boolean; error: boolean; empty: boolean; success: boolean };
        message?: {
            loading: string;
            error: string;
            empty: {
                title: string;
                description: string;
            };
        };
        itemCount?: number;
        loaderDisabled?: boolean;
        loaderLoading?: boolean;
        onLoadMore?: () => void;
    } = $props();
</script>

<GridContainer
    {status}
    {message}
    {itemCount}
    loader={{
        loadMore: onLoadMore,
        disabled: loaderDisabled,
        loading: loaderLoading
    }}
>
    {#snippet children({ footer })}
        <div data-testid="grid-success-content">Success content</div>
        <div data-testid="grid-footer-content">
            {@render footer()}
        </div>
    {/snippet}
</GridContainer>
