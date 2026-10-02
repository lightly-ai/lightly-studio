<script lang="ts">
    import type {
        MetadataJointAxisView,
        MetadataJointDistributionRequest
    } from '$lib/api/lightly_studio_local';
    import { DistributionPlotContainer } from '$lib/components/DatasetDistributionPanel';
    import { MetadataHeatmap, type HeatmapCellRect } from '$lib/components/MetadataHeatmap';
    import { useMetadataJointDistribution } from '$lib/hooks';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import JointAxisSelects from './JointAxisSelects/JointAxisSelects.svelte';
    import {
        filtersFromRect,
        formatBucketLabel,
        selectionFromFilters,
        selectJointMetadataKeys
    } from './jointSelection';

    interface Props {
        collectionId: string;
        /** The full sidebar filter. The server ignores the filters of the two axis keys. */
        filter: MetadataJointDistributionRequest['filters'];
    }

    const { collectionId, filter }: Props = $props();

    const metadataFilters = useMetadataFilters();
    const { metadataInfo, metadataValues, metadataBounds, categoricalMetadataValues } =
        metadataFilters;

    let selectedXKey = $state<string | undefined>(undefined);
    let selectedYKey = $state<string | undefined>(undefined);
    let binCount = $state(10);
    let chartHeight = $state(0);

    const keys = $derived(selectJointMetadataKeys($metadataInfo));
    const xKey = $derived(selectedXKey && keys.includes(selectedXKey) ? selectedXKey : keys[0]);
    const yKey = $derived(
        selectedYKey && keys.includes(selectedYKey) && selectedYKey !== xKey
            ? selectedYKey
            : keys.find((key) => key !== xKey)
    );

    const query = useMetadataJointDistribution(() => ({
        collectionId,
        xKey: xKey ?? '',
        yKey: yKey ?? '',
        binCount,
        filter: filter ?? undefined,
        enabled: xKey !== undefined && yKey !== undefined
    }));
    const distribution = $derived(query.data);
    const filterState = $derived({
        metadataValues: $metadataValues,
        categoricalMetadataValues: $categoricalMetadataValues,
        metadataBounds: $metadataBounds
    });
    const selection = $derived(
        distribution ? selectionFromFilters(distribution, filterState) : null
    );

    const toHeatmapAxis = (axis: MetadataJointAxisView) => ({
        name: axis.key,
        labels: axis.buckets.map((bucket) => formatBucketLabel(bucket, axis.type))
    });

    // Picking the key of the other axis swaps the two axes.
    const setXKey = (key: string) => {
        if (key === yKey) selectedYKey = xKey;
        selectedXKey = key;
    };
    const setYKey = (key: string) => {
        if (key === xKey) selectedXKey = yKey;
        selectedYKey = key;
    };

    const handleSelect = (rect: HeatmapCellRect) => {
        if (!distribution) return;
        const next = filtersFromRect(distribution, rect, filterState);
        if (!next) return;
        metadataFilters.updateMetadataValues(next.metadataValues);
        metadataFilters.updateCategoricalMetadataValues(next.categoricalMetadataValues);
    };
</script>

{#if xKey && yKey}
    <JointAxisSelects
        {keys}
        {xKey}
        {yKey}
        {binCount}
        onXKeyChange={setXKey}
        onYKeyChange={setYKey}
        onBinCountChange={(count) => (binCount = count)}
    />
    <p class="mt-2 text-xs text-muted-foreground">
        Click a cell or drag across cells to filter. Click a label to select a row or column.
    </p>
    <DistributionPlotContainer loading={query.isFetching && !distribution}>
        <div class="mt-2 min-h-0 flex-1" bind:clientHeight={chartHeight}>
            {#if query.error && !distribution}
                <p class="p-8 text-center text-sm text-destructive" role="alert">
                    Could not load the joint distribution.
                </p>
            {:else if distribution}
                <MetadataHeatmap
                    xAxis={toHeatmapAxis(distribution.x_axis)}
                    yAxis={toHeatmapAxis(distribution.y_axis)}
                    counts={distribution.counts}
                    {selection}
                    heightPx={chartHeight || 240}
                    onSelect={handleSelect}
                />
            {/if}
        </div>
    </DistributionPlotContainer>
{:else}
    <p class="p-8 text-center text-sm text-muted-foreground">
        Add at least two metadata fields to see a joint distribution.
    </p>
{/if}
