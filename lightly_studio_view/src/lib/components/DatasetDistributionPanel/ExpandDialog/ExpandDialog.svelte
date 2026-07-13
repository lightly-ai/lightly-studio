<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import {
        BarChart,
        type CategoryCount,
        type ChartMode,
        type ChartNormalize,
        type ChartSeries
    } from '$lib/components/BarChart';
    import DistributionConfigDialog from '../DistributionConfigDialog/DistributionConfigDialog.svelte';
    import PanelHeader from '../PanelHeader/PanelHeader.svelte';
    import { selectVisibleCounts } from '../selectVisibleCounts';
    import type { DistributionConfig } from '../types';

    interface Props {
        /** Two-way bound flag controlling dialog visibility. */
        open: boolean;
        /** Full class counts for the annotation path; the dialog applies `config` itself. */
        data: CategoryCount[];
        /**
         * Pre-shaped multi-series data for a metadata source. When provided, the
         * dialog renders these series (already sorted/top-N'd by the panel)
         * instead of `data`.
         */
        series?: ChartSeries[];
        /** Chart form for the metadata path (default 'bar'). */
        mode?: ChartMode;
        /** Count vs percentage for the metadata path (default 'count'). */
        normalize?: ChartNormalize;
        /** Header counts (supplied by the panel so both views agree). */
        classCount?: number;
        visibleClassCount?: number;
        totalCount?: number;
        /** Every category label, used to bound top-N and populate the manual selector. */
        allClasses?: string[];
        /** The applied view config, shared with the panel. */
        config: DistributionConfig;
        /** Noun for the header summary (e.g. 'annotations', 'samples'). */
        valueNoun?: string;
        /** Invoked when the user applies a new config from the expanded view. */
        onConfigChange: (config: DistributionConfig) => void;
        /** Toggles counts vs percentages; rendered only when provided (metadata sources). */
        onToggleNormalize?: () => void;
        onBarClick?: (item: CategoryCount) => void;
    }

    let {
        open = $bindable(),
        data,
        series,
        mode = 'bar',
        normalize = 'count',
        classCount,
        visibleClassCount,
        totalCount,
        allClasses,
        config,
        valueNoun = 'annotations',
        onConfigChange,
        onToggleNormalize,
        onBarClick
    }: Props = $props();

    let configDialogOpen = $state(false);

    const isMetadata = $derived(series !== undefined);

    // Annotation path applies the config here; metadata series arrive pre-shaped.
    const annotationVisible = $derived(selectVisibleCounts(data, config));

    const headerClassCount = $derived(classCount ?? data.length);
    const headerVisibleCount = $derived(visibleClassCount ?? annotationVisible.length);
    const headerTotal = $derived(totalCount ?? data.reduce((sum, item) => sum + item.count, 0));
    const configClasses = $derived(allClasses ?? data.map((item) => item.label));
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="flex h-[92vh] max-w-[94vw] flex-col sm:max-w-[94vw]">
        <Dialog.Header>
            <Dialog.Title>Class distribution</Dialog.Title>
            <Dialog.Description>Hover a bar for the full class name and count</Dialog.Description>
        </Dialog.Header>
        <PanelHeader
            {config}
            classCount={headerClassCount}
            visibleClassCount={headerVisibleCount}
            totalCount={headerTotal}
            {valueNoun}
            onConfigure={() => (configDialogOpen = true)}
            onShowAll={() => onConfigChange({ ...config, mode: 'topN', n: headerClassCount })}
            onToggleOrientation={() =>
                onConfigChange({
                    ...config,
                    orientation: config.orientation === 'horizontal' ? 'vertical' : 'horizontal'
                })}
            {onToggleNormalize}
            testIdPrefix="dataset-distribution-expanded"
        />
        <div class="min-h-0 flex-1 overflow-y-auto dark:[color-scheme:dark]">
            {#if isMetadata}
                <BarChart
                    {series}
                    {mode}
                    {normalize}
                    orientation={config.orientation}
                    maxHeightPx={560}
                />
            {:else}
                <BarChart
                    data={annotationVisible}
                    orientation={config.orientation}
                    maxHeightPx={560}
                    totalCount={headerTotal}
                    {onBarClick}
                />
            {/if}
        </div>
    </Dialog.Content>
</Dialog.Root>

<DistributionConfigDialog
    bind:open={configDialogOpen}
    allClasses={configClasses}
    {config}
    onApply={onConfigChange}
/>
