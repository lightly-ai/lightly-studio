<script lang="ts">
    import type { HistogramData } from '$lib/components/Histogram';
    import { Select, type SelectItem } from '$lib/components/Select';
    import { formatFloat, formatInteger } from '$lib/utils';
    import { ValueModeSelect, type ValueMode } from '../../PanelHeader/ValueModeSelect';
    import { HISTOGRAM_BIN_COUNT_ITEMS } from '../../types';

    interface Props {
        data: HistogramData;
        valueNoun: string;
        binCount: number;
        onBinCountChange?: (binCount: number) => void;
        valueMode: ValueMode;
        onValueModeChange?: (mode: ValueMode) => void;
    }

    const { data, valueNoun, binCount, onBinCountChange, valueMode, onValueModeChange }: Props =
        $props();

    const totalCount = $derived(data.counts.reduce((sum, count) => sum + count, 0));
    const binCountItems: SelectItem[] = HISTOGRAM_BIN_COUNT_ITEMS.map((count) => ({
        value: String(count),
        label: `${count} bins`
    }));
</script>

<div class="flex flex-wrap items-center justify-between gap-2">
    <span
        class="text-xs text-muted-foreground"
        data-testid="dataset-distribution-expanded-histogram-summary"
    >
        {valueMode === 'percentage' ? '100% of ' : ''}{formatInteger(totalCount)}
        {valueNoun} · {data.counts.length}
        {data.counts.length === 1 ? 'bin' : 'bins'} · {formatFloat(data.binEdges[0])}–{formatFloat(
            data.binEdges[data.binEdges.length - 1]
        )}
    </span>
    <div class="flex items-center gap-1">
        {#if onValueModeChange}
            <ValueModeSelect
                value={valueMode}
                testId="dataset-distribution-expanded-histogram-value-mode"
                onChange={onValueModeChange}
            />
        {/if}
        {#if onBinCountChange}
            <Select
                items={binCountItems}
                value={String(binCount)}
                size="xs"
                class="w-28"
                testId="dataset-distribution-expanded-bin-count"
                selectProps={{ 'aria-label': 'Histogram bin count' }}
                onValueChange={(value) => onBinCountChange(Number(value))}
            />
        {/if}
    </div>
</div>
