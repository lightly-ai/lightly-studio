<script lang="ts">
    import { Button } from '$lib/components/ui';
    import { ChartNetwork } from '@lucide/svelte';
    import type { useRouteType } from '$lib/hooks/useRouteType/useRouteType';

    const {
        routeType,
        hasEmbeddings,
        showPlot,
        setShowPlot
    }: {
        routeType: ReturnType<typeof useRouteType>;
        hasEmbeddings: boolean;
        showPlot: boolean;
        setShowPlot: (value: boolean) => void;
    } = $props();
</script>

{#if (routeType.isSamples || routeType.isVideos) && hasEmbeddings}
    <Button
        class="flex items-center space-x-1"
        data-testid="toggle-plot-button"
        variant={showPlot ? 'default' : 'ghost'}
        onclick={() => setShowPlot(!showPlot)}
    >
        <ChartNetwork class="size-4" />
        <span>Show Embeddings</span>
    </Button>
{/if}
