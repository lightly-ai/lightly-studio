<script lang="ts">
    import { X } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import SourceGroupSelector from '../SourceGroupSelector/SourceGroupSelector.svelte';
    import HistogramToolbar from '../HistogramToolbar/HistogramToolbar.svelte';
    import PanelHeader from '../PanelHeader/PanelHeader.svelte';
    import { MetadataCategoricalFilter } from '../MetadataCategoricalFilter';
    import { CATEGORICAL_DISTRIBUTION_SORT_LABELS } from '../types';
    import type { useDistributionPanel } from '../useDistributionPanel.svelte';

    interface Props {
        title: string;
        panel: ReturnType<typeof useDistributionPanel>;
        histogramBinCount: number;
        onHistogramBinCountChange?: (binCount: number) => void;
        onCategoricalRetry?: () => void;
        onClose?: () => void;
        onOpenConfig: () => void;
        onOpenExpand: () => void;
        onOpenHistogramExpand: () => void;
    }

    const {
        title,
        panel,
        histogramBinCount,
        onHistogramBinCountChange,
        onCategoricalRetry,
        onClose,
        onOpenConfig,
        onOpenExpand,
        onOpenHistogramExpand
    }: Props = $props();
</script>

<div class="flex items-center justify-between">
    <Typography variant="h5" component="h2" className="text-foreground">
        {title}
    </Typography>
    {#if onClose}
        <Button
            variant="ghost"
            icon={X}
            ariaLabel="Close distribution panel"
            buttonProps={{
                size: 'sm',
                class: 'h-8 w-8 p-0',
                onclick: onClose,
                'data-testid': 'dataset-distribution-close-button'
            }}
        />
    {/if}
</div>
{#if panel.hasSourceSelector}
    <SourceGroupSelector
        sourceItems={panel.sourceItems}
        groupItems={panel.groupItems}
        activeSourceId={panel.activeSource.id}
        activeGroupId={panel.activeGroup?.id}
        groupLabel={panel.activeSource.groupLabel ?? 'Field'}
        onSourceChange={(value) => {
            panel.setSelectedSourceId(value);
            panel.setSelectedGroupId(undefined);
        }}
        onGroupChange={(value) => panel.setSelectedGroupId(value)}
    />
{/if}
{#if panel.activeHistogram}
    <HistogramToolbar
        histogram={panel.activeHistogram}
        histogramTotal={panel.histogramTotal}
        valueNoun={panel.valueNoun}
        {histogramBinCount}
        binCountItems={panel.binCountItems}
        {onHistogramBinCountChange}
        onExpand={onOpenHistogramExpand}
    />
{:else if panel.activeCategorical && panel.activeGroup}
    <MetadataCategoricalFilter
        buckets={panel.activeCategorical.buckets}
        selectedValues={panel.activeCategorical.selectedValues}
        loading={panel.activeCategorical.loading}
        onToggle={panel.handleCategoricalFilterToggle}
        onClear={panel.handleCategoricalFilterClear}
    />
    {#if panel.activeCategorical.error}
        <div
            class="mt-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
        >
            <div class="font-medium">Unable to refresh categorical values</div>
            <div class="mt-1">{panel.activeCategorical.error}</div>
            {#if onCategoricalRetry}
                <Button
                    variant="ghost"
                    buttonProps={{
                        size: 'sm',
                        class: 'mt-2 h-8 px-2 text-sm',
                        onclick: onCategoricalRetry
                    }}
                    ariaLabel="Retry categorical refresh"
                >
                    Retry
                </Button>
            {/if}
        </div>
    {/if}
    {#if panel.categoricalData.length > 0}
        <div class="mt-2">
            <PanelHeader
                config={panel.categoricalConfig}
                classCount={panel.categoricalData.length}
                visibleClassCount={panel.visible.length}
                totalCount={panel.totalCount}
                valueNoun={panel.valueNoun}
                categoryNoun="value"
                categoryNounPlural="values"
                sortLabels={CATEGORICAL_DISTRIBUTION_SORT_LABELS}
                onConfigure={onOpenConfig}
                onShowAll={() =>
                    panel.setCategoricalConfig({
                        ...panel.categoricalConfig,
                        mode: 'topN',
                        n: panel.categoricalData.length
                    })}
                onToggleOrientation={() =>
                    panel.setCategoricalConfig({
                        ...panel.categoricalConfig,
                        orientation:
                            panel.categoricalConfig.orientation === 'horizontal'
                                ? 'vertical'
                                : 'horizontal'
                    })}
                onExpand={onOpenExpand}
            />
        </div>
    {/if}
{:else if panel.activeData.length > 0}
    <div class="mt-2">
        <PanelHeader
            config={panel.config}
            classCount={panel.activeData.length}
            visibleClassCount={panel.visible.length}
            totalCount={panel.showTotalCount ? panel.totalCount : undefined}
            valueNoun={panel.valueNoun}
            onConfigure={onOpenConfig}
            onShowAll={() =>
                panel.applyConfig({
                    ...panel.config,
                    mode: 'topN',
                    n: panel.activeData.length
                })}
            onToggleOrientation={() =>
                panel.applyConfig({
                    ...panel.config,
                    orientation:
                        panel.config.orientation === 'horizontal' ? 'vertical' : 'horizontal'
                })}
            onExpand={onOpenExpand}
        />
    </div>
{/if}
