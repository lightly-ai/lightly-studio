<script lang="ts">
    import {
        useMetadataDistributionSeries,
        type MetadataDistributionSeriesInput,
        type MetadataDistributionSeriesResult
    } from '$lib/hooks/useMetadataDistribution/useMetadataDistributionSeries';

    interface Props {
        collectionId: string;
        /** Metadata key to aggregate; queries stay idle until it is set. */
        metadataKey: string | undefined;
        /** One entry per overlaid series (current selection + compared tags). */
        series: MetadataDistributionSeriesInput[];
        /** Which endpoint to fetch from (default 'metadata'). */
        endpoint?: 'metadata' | 'nn_distance';
        /** Fetched, shaped result surfaced back to the panel. */
        result: MetadataDistributionSeriesResult;
    }

    let {
        collectionId,
        metadataKey,
        series,
        endpoint = 'metadata',
        result = $bindable()
    }: Props = $props();

    // Headless: mounted only while a metadata source is active so `createQueries`
    // (and its QueryClient requirement) never runs for annotation-only panels.
    const query = useMetadataDistributionSeries(() => ({
        collectionId,
        key: metadataKey,
        series,
        endpoint
    }));

    $effect(() => {
        result = {
            series: query.series,
            chartMode: query.chartMode,
            isLoading: query.isLoading,
            isError: query.isError
        };
    });
</script>
