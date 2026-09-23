<script lang="ts">
    import { Maximize2 as Maximize2Icon } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { Select, type SelectItem } from '$lib/components/Select';
    import { formatFloat, formatInteger } from '$lib/utils';
    import type { HistogramData } from '$lib/components/Histogram';
    import { ValueModeSelect, type ValueMode } from '../PanelHeader/ValueModeSelect';

    interface Props {
        histogram: HistogramData;
        histogramTotal: number;
        valueNoun: string;
        histogramBinCount: number;
        binCountItems: SelectItem[];
        onHistogramBinCountChange?: (binCount: number) => void;
        valueMode?: ValueMode;
        onValueModeChange?: (mode: ValueMode) => void;
        onExpand: () => void;
    }

    const {
        histogram,
        histogramTotal,
        valueNoun,
        histogramBinCount,
        binCountItems,
        onHistogramBinCountChange,
        valueMode = 'number',
        onValueModeChange,
        onExpand
    }: Props = $props();
</script>

<div class="mt-2 flex flex-wrap items-center justify-between gap-2">
    <span
        class="text-xs text-muted-foreground"
        data-testid="dataset-distribution-histogram-summary"
    >
        {valueMode === 'percentage' ? '100% of ' : ''}{formatInteger(histogramTotal)}
        {valueNoun} · {histogram.counts.length}
        {histogram.counts.length === 1 ? 'bin' : 'bins'} · {formatFloat(
            histogram.binEdges[0]
        )}–{formatFloat(histogram.binEdges[histogram.binEdges.length - 1])}
    </span>
    <div class="flex items-center gap-1">
        {#if onValueModeChange}
            <ValueModeSelect
                value={valueMode}
                testId="dataset-distribution-histogram-value-mode"
                onChange={onValueModeChange}
            />
        {/if}
        {#if onHistogramBinCountChange}
            <Select
                items={binCountItems}
                value={String(histogramBinCount)}
                size="xs"
                class="w-24"
                testId="dataset-distribution-bin-count"
                selectProps={{ 'aria-label': 'Histogram bin count' }}
                onValueChange={(value) => onHistogramBinCountChange(Number(value))}
            />
        {/if}
        <Button
            variant="ghost"
            icon={Maximize2Icon}
            ariaLabel="Expand distribution"
            buttonProps={{
                size: 'sm',
                class: 'h-8 w-8 p-0',
                onclick: onExpand,
                'data-testid': 'dataset-distribution-histogram-expand'
            }}
        />
    </div>
</div>
