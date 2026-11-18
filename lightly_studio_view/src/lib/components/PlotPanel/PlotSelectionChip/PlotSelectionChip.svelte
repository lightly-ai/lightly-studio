<script lang="ts">
    import SquareDashed from '@lucide/svelte/icons/square-dashed';
    import MousePointerClick from '@lucide/svelte/icons/mouse-pointer-click';
    import X from '@lucide/svelte/icons/x';
    import { Button } from '$lib/components/ui/button';
    import type { PickHint } from './PlotSelectionChip.helpers';

    interface Props {
        // null renders only the hint, for a plot with nothing selected.
        selectionKind: 'picks' | 'region' | null;
        count: number;
        itemLabel: string;
        onClear: () => void;
        pickHint: PickHint | null;
    }

    let { selectionKind, count, itemLabel, onClear, pickHint }: Props = $props();

    const label = $derived(
        selectionKind === 'picks'
            ? `${count} picked`
            : `${count} ${count === 1 ? itemLabel : `${itemLabel}s`}`
    );
</script>

<!-- Styled like the plot tool pill. Only the clear button takes the pointer, so the chip never
     blocks hovering the points under it. -->
<div
    class="pointer-events-none flex h-[30px] w-fit max-w-full items-center gap-2 rounded-lg border border-white/10 bg-black/60 px-2 text-xs text-white backdrop-blur-sm"
    data-testid="plot-selection-chip"
>
    {#if selectionKind !== null}
        {#if selectionKind === 'picks'}
            <MousePointerClick class="size-3.5 shrink-0" />
        {:else}
            <SquareDashed class="size-3.5 shrink-0" />
        {/if}
        <span class="whitespace-nowrap font-medium">{label}</span>
        <Button
            variant="ghost"
            size="icon"
            class="pointer-events-auto size-4 shrink-0 text-white/60 hover:bg-transparent hover:text-white"
            onclick={onClear}
            title="Clear plot filter (Esc)"
            aria-label="Clear plot filter"
        >
            <X />
        </Button>
    {/if}
    {#if pickHint !== null}
        {#if selectionKind !== null}
            <span class="h-4 w-px shrink-0 bg-white/10"></span>
        {/if}
        <span class="min-w-0 truncate text-[11.5px] text-white/60" data-testid="plot-pick-hint">
            <kbd class="rounded border border-white/10 bg-white/10 px-1">Shift</kbd> + click to
            <span class="text-white">{pickHint}</span>
        </span>
    {/if}
</div>
