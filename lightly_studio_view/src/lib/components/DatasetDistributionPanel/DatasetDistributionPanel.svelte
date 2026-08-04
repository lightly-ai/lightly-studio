<script lang="ts">
    import { type CategoryCount } from '$lib/components/BarChart';
    import { type HistogramRange } from '$lib/components/Histogram';
    import DistributionConfigDialog from './DistributionConfigDialog/DistributionConfigDialog.svelte';
    import ExpandDialog from './ExpandDialog/ExpandDialog.svelte';
    import HistogramExpandDialog from './HistogramExpandDialog/HistogramExpandDialog.svelte';
    import DatasetDistributionHeader from './DatasetDistributionHeader/DatasetDistributionHeader.svelte';
    import DatasetDistributionContent from './DatasetDistributionContent/DatasetDistributionContent.svelte';
    import { CATEGORICAL_DISTRIBUTION_SORT_LABELS, type DistributionSource } from './types';
    import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';
    import type { CategoricalMetadataValue } from '$lib/services/types';
    import { useDistributionPanel } from './useDistributionPanel.svelte';

    interface Props {
        data?: CategoryCount[];
        sources?: DistributionSource[];
        title?: string;
        topN?: number;
        onClose?: () => void;
        onBarClick?: (item: CategoryCount) => void;
        onCountModeChange?: (mode: AnnotationCountMode) => void;
        initialCountMode?: AnnotationCountMode;
        onHistogramRangeSelect?: (groupId: string, range: HistogramRange) => void;
        histogramBinCount?: number;
        onHistogramBinCountChange?: (binCount: number) => void;
        onCategoricalValueToggle?: (groupId: string, value: CategoricalMetadataValue) => void;
        onCategoricalValuesClear?: (groupId: string) => void;
        onCategoricalRetry?: () => void;
    }

    const {
        data,
        sources,
        title = 'Distribution',
        topN = 20,
        onClose,
        onBarClick,
        onCountModeChange,
        initialCountMode = AnnotationCountMode.OBJECTS,
        onHistogramRangeSelect,
        histogramBinCount = 20,
        onHistogramBinCountChange,
        onCategoricalValueToggle,
        onCategoricalValuesClear,
        onCategoricalRetry
    }: Props = $props();

    const panel = useDistributionPanel(() => ({
        sources,
        data,
        topN,
        initialCountMode,
        onCountModeChange,
        onHistogramRangeSelect,
        onCategoricalValueToggle,
        onCategoricalValuesClear
    }));

    let configDialogOpen = $state(false);
    let expandOpen = $state(false);
    let histogramExpandOpen = $state(false);
</script>

<div
    class="flex h-full min-w-0 flex-1 flex-col rounded-[1vw] bg-card p-4"
    data-testid="dataset-distribution-panel"
>
    <DatasetDistributionHeader
        {title}
        {panel}
        {histogramBinCount}
        {onHistogramBinCountChange}
        {onCategoricalRetry}
        {onClose}
        onOpenConfig={() => (configDialogOpen = true)}
        onOpenExpand={() => (expandOpen = true)}
        onOpenHistogramExpand={() => (histogramExpandOpen = true)}
    />
    <DatasetDistributionContent
        {panel}
        {onHistogramRangeSelect}
        {onBarClick}
        {onCategoricalRetry}
    />
</div>

{#if panel.activeHistogram}
    <HistogramExpandDialog
        bind:open={histogramExpandOpen}
        data={panel.activeHistogram}
        label={panel.activeGroup?.label ?? panel.activeSource.label}
        selectedRange={panel.activeHistogramRange}
        valueNoun={panel.valueNoun}
        binCount={histogramBinCount}
        onBinCountChange={onHistogramBinCountChange}
        onRangeSelect={onHistogramRangeSelect ? panel.handleHistogramRangeSelect : undefined}
    />
{:else}
    <DistributionConfigDialog
        bind:open={configDialogOpen}
        allClasses={panel.displayedData.map((item) => item.label)}
        items={panel.configurationItems}
        config={panel.activeViewConfig}
        showCountMode={!panel.activeCategorical}
        itemNoun={panel.activeCategorical ? 'value' : 'class'}
        itemNounPlural={panel.activeCategorical ? 'values' : 'classes'}
        sortLabels={panel.activeCategorical ? CATEGORICAL_DISTRIBUTION_SORT_LABELS : undefined}
        onApply={panel.applyConfig}
    />
    <ExpandDialog
        bind:open={expandOpen}
        data={panel.displayedData}
        config={panel.activeViewConfig}
        valueNoun={panel.valueNoun}
        categoryNoun={panel.activeCategorical ? 'value' : 'class'}
        categoryNounPlural={panel.activeCategorical ? 'values' : 'classes'}
        sortLabels={panel.activeCategorical ? CATEGORICAL_DISTRIBUTION_SORT_LABELS : undefined}
        showCountMode={!panel.activeCategorical}
        onConfigChange={panel.applyConfig}
        onBarClick={panel.activeCategorical ? panel.handleCategoricalBarClick : onBarClick}
    />
{/if}
