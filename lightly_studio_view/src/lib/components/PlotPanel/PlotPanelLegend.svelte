<script lang="ts">
    import { cn } from '$lib/utils';
    import {
        EXCLUDED_BY_FILTERS_CATEGORY,
        EXCLUDED_BY_FILTERS_LABEL,
        INCLUDED_BY_FILTERS_CATEGORY,
        INCLUDED_BY_FILTERS_LABEL
    } from './plotCategories';

    interface LegendEntry {
        cat: number;
        label: string;
        color: string;
        hidden: boolean;
    }

    interface Props {
        categoryColors: string[];
        excludedLabel?: string;
        includedLabel?: string;
        excludedHidden?: boolean;
        includedHidden?: boolean;
        legendEntries?: LegendEntry[];
        onToggleCategory?: (cat: number) => void;
        onDoubleClickCategory?: (cat: number) => void;
    }

    let {
        categoryColors,
        excludedLabel = EXCLUDED_BY_FILTERS_LABEL,
        includedLabel = INCLUDED_BY_FILTERS_LABEL,
        excludedHidden = false,
        includedHidden = false,
        legendEntries = [],
        onToggleCategory,
        onDoubleClickCategory
    }: Props = $props();

    // Reserved rows toggle on click but never isolate on double-click (a no-op for a binary row).
    const reservedRows = $derived([
        {
            cat: EXCLUDED_BY_FILTERS_CATEGORY,
            label: excludedLabel,
            color: categoryColors[EXCLUDED_BY_FILTERS_CATEGORY],
            hidden: excludedHidden
        },
        {
            cat: INCLUDED_BY_FILTERS_CATEGORY,
            label: includedLabel,
            color: categoryColors[INCLUDED_BY_FILTERS_CATEGORY],
            hidden: includedHidden
        }
    ]);
</script>

<div
    class="absolute bottom-1 left-3 flex max-h-[calc(100%-0.5rem)] max-w-48 flex-col items-start gap-1 overflow-hidden rounded-md border border-white/10 bg-black/60 px-2 py-1 text-xs text-muted-foreground backdrop-blur-sm"
    data-testid="plot-legend"
>
    <div class="flex w-full flex-col gap-1 overflow-y-auto dark:[color-scheme:dark]">
        {#each legendEntries.toSorted( (a, b) => a.label.localeCompare(b.label) ) as entry (entry.cat)}
            <button
                type="button"
                class={cn(
                    'flex w-full cursor-pointer items-center gap-1.5 rounded text-left transition-opacity hover:opacity-80',
                    entry.hidden && 'opacity-40'
                )}
                data-testid={`plot-legend-entry-${entry.cat}`}
                aria-pressed={entry.hidden}
                title={entry.hidden ? 'Show category' : 'Hide category'}
                onclick={() => onToggleCategory?.(entry.cat)}
                ondblclick={() => onDoubleClickCategory?.(entry.cat)}
            >
                <span class="legend-dot shrink-0" style={`background-color: ${entry.color}`}></span>
                <span class="min-w-0 truncate" title={entry.label}>{entry.label}</span>
            </button>
        {/each}
        {#if legendEntries.length > 0}
            <span class="my-0.5 w-full shrink-0 border-t border-white/10"></span>
        {/if}
        {#each reservedRows as row (row.cat)}
            <button
                type="button"
                class={cn(
                    'flex w-full shrink-0 cursor-pointer items-center gap-1.5 rounded text-left transition-opacity hover:opacity-80',
                    row.hidden && 'opacity-40'
                )}
                data-testid={`plot-legend-entry-${row.cat}`}
                aria-pressed={row.hidden}
                title={row.hidden ? 'Show category' : 'Hide category'}
                onclick={() => onToggleCategory?.(row.cat)}
            >
                <span class="legend-dot shrink-0" style={`background-color: ${row.color}`}></span>
                <span class="min-w-0 truncate" title={row.label}>{row.label}</span>
            </button>
        {/each}
    </div>
</div>

<style>
    .legend-dot {
        display: inline-block;
        height: 0.75rem;
        width: 0.75rem;
        border-radius: 9999px;
    }
</style>
