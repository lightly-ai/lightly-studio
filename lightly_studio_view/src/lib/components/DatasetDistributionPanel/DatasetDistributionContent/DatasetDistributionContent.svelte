<script lang="ts">
    import DistributionChart from './DistributionChart/DistributionChart.svelte';
    import type { CategoryCount } from '$lib/components/BarChart';
    import type { HistogramRange } from '$lib/components/Histogram';
    import type { useDistributionPanel } from './useDistributionPanel.svelte';

    interface Props {
        panel: ReturnType<typeof useDistributionPanel>;
        onHistogramRangeSelect?: (groupId: string, range: HistogramRange) => void;
        onBarClick?: (item: CategoryCount) => void;
        onCategoricalRetry?: () => void;
    }

    const { panel, onHistogramRangeSelect, onBarClick, onCategoricalRetry }: Props = $props();
</script>

<DistributionChart
    activeHistogram={panel.activeHistogram}
    activeCategorical={panel.activeCategorical}
    viewConfig={panel.activeViewConfig}
    visible={panel.visible}
    totalCount={panel.totalCount}
    selectedRange={panel.activeHistogramRange}
    onHistogramRangeSelect={onHistogramRangeSelect ? panel.handleHistogramRangeSelect : undefined}
    onBarClick={panel.activeCategorical ? panel.handleCategoricalBarClick : onBarClick}
    {onCategoricalRetry}
/>
