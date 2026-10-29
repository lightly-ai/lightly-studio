<script lang="ts">
    import type { TileChip } from './getTileChips';

    interface Props {
        chips: TileChip[];
        /** Image tiles keep the bottom for pills and captions; annotation tiles keep the top for the box label. */
        position?: 'top' | 'bottom';
    }

    const { chips, position = 'top' }: Props = $props();
</script>

{#if chips.length > 0}
    <!-- Left edge, clear of the selection box (top right) and the value badge (bottom right). -->
    <div
        class="pointer-events-none absolute left-1 z-10 flex max-h-[calc(100%-2.5rem)] flex-col gap-0.5 overflow-hidden {position ===
        'top'
            ? 'right-8 top-1 items-start'
            : 'bottom-1 right-14 items-start justify-end'}"
        data-testid="tile-field-chips"
    >
        {#each chips as chip (chip.id)}
            <span
                class="pointer-events-auto box-border block h-5 max-w-full shrink-0 truncate rounded bg-black/60 px-1.5 text-xs font-medium leading-5 text-white backdrop-blur-sm"
                title={chip.title}
            >
                {chip.text}
            </span>
        {/each}
    </div>
{/if}
