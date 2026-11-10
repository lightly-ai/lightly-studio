<script lang="ts">
    import { Trash2 } from '@lucide/svelte';
    import { CardCloseButton } from '../CardCloseButton';
    import { ColorDot } from '../ColorDot';

    interface Props {
        sources: { collection_id: string; name: string }[];
        /** The annotation source the annotation is in. */
        sourceId: string;
        confidence?: number | null;
        /** Whether to mark the source with its color, as the canvas does when coloring by source. */
        showSourceColor: boolean;
        /** Replaces the source button, for example "Move to…" while the move list is open. */
        title?: string;
        onMove: () => void;
        onRemove: () => void;
        onClose: () => void;
    }

    const {
        sources,
        sourceId,
        confidence,
        showSourceColor,
        title,
        onMove,
        onRemove,
        onClose
    }: Props = $props();
    const sourceName = $derived(
        sources.find((source) => source.collection_id === sourceId)?.name ?? 'Annotation source'
    );
    // With a single source there is nowhere to move to, so the move list would stay empty.
    const canMove = $derived(sources.some((source) => source.collection_id !== sourceId));
</script>

<div class="flex items-center gap-1">
    {#if title}
        <span class="px-2 py-0.5 text-xs font-medium">{title}</span>
    {:else}
        <button
            type="button"
            class="inline-flex min-w-0 items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs hover:bg-accent disabled:cursor-default disabled:hover:bg-transparent"
            title={canMove
                ? 'Move to another annotation source'
                : 'No other annotation source to move to'}
            disabled={!canMove}
            onclick={onMove}
        >
            {#if showSourceColor}
                <ColorDot label={sourceName} kind="source" testId="annotation-card-source-dot" />
            {/if}
            <span class="truncate">{sourceName}</span>
        </button>
    {/if}
    {#if confidence != null}
        <span class="text-xs text-muted-foreground">Confidence {confidence.toFixed(2)}</span>
    {/if}
    <span class="flex-1"></span>
    <button
        type="button"
        class="inline-flex size-6 items-center justify-center rounded-md text-muted-foreground hover:text-foreground"
        aria-label="Delete annotation"
        title="Delete annotation (Del)"
        onclick={onRemove}
    >
        <Trash2 class="size-4" />
    </button>
    <CardCloseButton {onClose} />
</div>
