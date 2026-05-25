<script lang="ts">
    import { cn } from '$lib/utils';

    interface LegendEntry {
        cat: number;
        label: string;
        color: string;
        hidden: boolean;
    }

    interface Props {
        categoryColors: string[];
        filteredLabel?: string;
        legendEntries?: LegendEntry[];
        onToggleCategory?: (cat: number) => void;
        onDoubleClickCategory?: (cat: number) => void;
    }

    let {
        categoryColors,
        filteredLabel = 'Filtered',
        legendEntries = [],
        onToggleCategory,
        onDoubleClickCategory
    }: Props = $props();
</script>

<div
    class="absolute bottom-1 left-3 flex max-h-[calc(100%-0.5rem)] flex-col items-start gap-1 overflow-hidden rounded-md border border-white/10 bg-black/60 px-2 py-1 text-xs text-muted-foreground backdrop-blur-sm"
    data-testid="plot-legend"
>
    <span class="flex shrink-0 items-center gap-1.5">
        <span class="legend-dot" style={`background-color: ${categoryColors[0]}`}></span>
        Not Filtered
    </span>
    <span class="flex shrink-0 items-center gap-1.5">
        <span class="legend-dot" style={`background-color: ${categoryColors[1]}`}></span>
        {filteredLabel}
    </span>
    {#if legendEntries.length > 0}
        <span class="my-0.5 w-full shrink-0 border-t border-white/10"></span>
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
                    <span class="legend-dot shrink-0" style={`background-color: ${entry.color}`}
                    ></span>
                    <span class="truncate">{entry.label}</span>
                </button>
            {/each}
        </div>
    {/if}
</div>

<style>
    .legend-dot {
        display: inline-block;
        height: 0.75rem;
        width: 0.75rem;
        border-radius: 9999px;
    }
</style>
