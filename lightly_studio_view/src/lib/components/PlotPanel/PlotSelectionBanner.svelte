<script lang="ts">
    import Button from '$lib/components/ui/button/button.svelte';

    type Props = {
        selectionCount: number;
        selectionApplied?: boolean;
        showPlot: boolean;
        onClear: () => void;
        onToggleSelectionApplied?: () => void;
        onShowPlot?: () => void;
        canShowPlot?: boolean;
        itemLabel?: string;
    };

    let {
        selectionCount,
        selectionApplied = true,
        showPlot,
        onClear,
        onToggleSelectionApplied = () => {},
        onShowPlot = () => {},
        canShowPlot = true,
        itemLabel = 'sample'
    }: Props = $props();

    const itemLabelText = $derived(selectionCount === 1 ? itemLabel : `${itemLabel}s`);
</script>

<div
    class="flex flex-wrap items-center gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2.5"
    data-testid="plot-selection-banner"
>
    <div class="flex min-w-0 flex-1 items-start gap-3">
        <span class="mt-1 size-2 shrink-0 rounded-full bg-amber-400" aria-hidden="true"></span>
        <div class="min-w-0">
            <div class="text-sm font-medium text-foreground">
                Plot selection active: {selectionCount} {itemLabelText}
            </div>
            <div class="text-xs text-muted-foreground">
                {#if selectionApplied}
                    The grid is limited to the {itemLabelText} selected in the embedding plot.
                {:else}
                    Selection is saved but not applied to the grid.
                {/if}
            </div>
        </div>
    </div>

    <div class="flex flex-wrap items-center gap-2">
        <Button
            variant="outline"
            size="sm"
            onclick={onToggleSelectionApplied}
            data-testid="plot-selection-banner-toggle-apply"
        >
            {selectionApplied ? 'Disable selection' : 'Re-enable selection'}
        </Button>
        {#if canShowPlot && !showPlot}
            <Button
                variant="outline"
                size="sm"
                onclick={onShowPlot}
                data-testid="plot-selection-banner-show-plot"
            >
                Show plot
            </Button>
        {/if}
        <Button
            variant="outline"
            size="sm"
            onclick={onClear}
            data-testid="plot-selection-banner-clear"
        >
            Clear selection
        </Button>
    </div>
</div>
