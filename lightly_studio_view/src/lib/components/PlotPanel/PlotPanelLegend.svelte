<script lang="ts">
    const CATEGORIES = [
        { label: 'Remaining', index: 0 },
        { label: 'Filtered', index: 1 }
    ];

    let {
        categoryColors,
        hiddenCategories,
        onToggleCategory
    }: {
        categoryColors: string[];
        hiddenCategories: Set<number>;
        onToggleCategory: (category: number) => void;
    } = $props();
</script>

<div
    class="absolute bottom-1 left-3 flex items-start gap-1.5 rounded-md border border-white/10 bg-black/60 px-2 py-1 text-xs text-muted-foreground backdrop-blur-sm"
    data-testid="plot-legend"
>
    <div class="flex flex-col items-start gap-1">
        {#each CATEGORIES as { label, index }}
            <button
                class="legend-item flex items-center gap-1.5 transition-opacity"
                class:opacity-40={hiddenCategories.has(index)}
                onclick={() => onToggleCategory(index)}
                title={hiddenCategories.has(index) ? `Show ${label}` : `Hide ${label}`}
            >
                <span class="legend-dot" style={`background-color: ${categoryColors[index]}`}
                ></span>
                {label}
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

    .legend-item {
        background: none;
        border: none;
        padding: 0;
        cursor: pointer;
        color: inherit;
        font: inherit;
    }
</style>
