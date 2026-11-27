<script lang="ts">
    import Sparkles from '@lucide/svelte/icons/sparkles';
    import X from '@lucide/svelte/icons/x';
    import { fly } from 'svelte/transition';

    interface Props {
        selectedCount: number;
        onClear: () => void;
        // Shown only where the selected samples can be auto-labeled.
        onAutoLabel?: () => void;
    }

    let { selectedCount, onClear, onAutoLabel }: Props = $props();
</script>

{#if selectedCount > 0}
    <div
        class="pointer-events-none absolute bottom-4 left-1/2 z-30 -translate-x-1/2"
        transition:fly={{ y: 20, duration: 200 }}
    >
        <div
            class="pointer-events-auto flex items-center gap-3 rounded-xl border border-primary/30 bg-primary/90 px-4 py-2 shadow-lg backdrop-blur-sm"
        >
            <span class="text-sm font-medium text-primary-foreground">
                {selectedCount} selected
            </span>
            {#if onAutoLabel}
                <button
                    class="flex items-center gap-1.5 rounded-md bg-primary-foreground/15 px-2 py-0.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-foreground/25"
                    onclick={onAutoLabel}
                    data-testid="auto-label-selection-button"
                >
                    <Sparkles class="h-3.5 w-3.5" />
                    Auto-label
                </button>
            {/if}
            <button
                class="h-6.5 w-6.5 flex items-center justify-center rounded-full text-primary-foreground opacity-80 transition-[background-color,opacity,transform] duration-150 hover:scale-105 hover:bg-primary-foreground/10 hover:opacity-100"
                aria-label="Clear selection"
                onclick={onClear}
                data-testid="clear-selection-button"
            >
                <X class="h-4 w-4" />
            </button>
        </div>
    </div>
{/if}
