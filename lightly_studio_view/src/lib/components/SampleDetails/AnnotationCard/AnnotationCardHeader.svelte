<script lang="ts">
    import { Trash2, X } from '@lucide/svelte';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { getLabelColor } from '$lib/utils';

    interface Props {
        sourceName: string;
        confidence?: number | null;
        /** Replaces the source button, for example "Move to…" while the move list is open. */
        title?: string;
        onMove: () => void;
        onRemove: () => void;
        onClose: () => void;
    }

    const { sourceName, confidence, title, onMove, onRemove, onClose }: Props = $props();
    const { customLabelColorsStore } = useCustomLabelColors();
    const iconButtonClass =
        'inline-flex size-6 items-center justify-center rounded-md text-muted-foreground hover:text-foreground';
</script>

<div class="flex items-center gap-1">
    {#if title}
        <span class="px-2 py-0.5 text-xs font-medium">{title}</span>
    {:else}
        <button
            type="button"
            class="inline-flex min-w-0 items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs hover:bg-accent"
            title="Move to another annotation source"
            onclick={onMove}
        >
            <span
                class="size-2 shrink-0 rounded-full"
                style:background-color={getLabelColor($customLabelColorsStore, sourceName)}
            ></span>
            <span class="truncate">{sourceName}</span>
        </button>
    {/if}
    {#if confidence != null}
        <span class="text-xs text-muted-foreground">Confidence {confidence.toFixed(2)}</span>
    {/if}
    <span class="flex-1"></span>
    <button
        type="button"
        class={iconButtonClass}
        aria-label="Delete annotation"
        title="Delete annotation (Del)"
        onclick={onRemove}
    >
        <Trash2 class="size-4" />
    </button>
    <button
        type="button"
        class={iconButtonClass}
        aria-label="Close"
        title="Close (Esc)"
        onclick={onClose}
    >
        <X class="size-4" />
    </button>
</div>
