<script lang="ts">
    import { cn } from '$lib/utils';
    import type { Snippet } from 'svelte';

    interface Props {
        /** Whether the annotation that is dragged can be moved here. */
        canDrop: boolean;
        /** The annotation source name, for screen readers. */
        sourceName: string;
        onDrop: () => void;
        children: Snippet;
    }

    const { canDrop, sourceName, onDrop, children }: Props = $props();

    let isOver = $state(false);
    const isHighlighted = $derived(canDrop && isOver);

    // A drag that ends elsewhere (Escape, a drop outside) fires no dragleave here.
    $effect(() => {
        if (!canDrop) isOver = false;
    });

    function handleDragOver(event: DragEvent) {
        if (!canDrop) return;
        // Cancelling dragover is what allows the drop.
        event.preventDefault();
        if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
        isOver = true;
    }

    function handleDragLeave(event: DragEvent) {
        // Moving onto a child element fires dragleave on the zone too.
        const next = event.relatedTarget;
        if (next instanceof Node && (event.currentTarget as HTMLElement).contains(next)) return;
        isOver = false;
    }

    function handleDrop(event: DragEvent) {
        isOver = false;
        if (!canDrop) return;
        event.preventDefault();
        onDrop();
    }
</script>

<div
    role="region"
    aria-label={`Annotation source ${sourceName}`}
    data-testid="annotation-source-drop-zone"
    data-drop-highlighted={isHighlighted}
    class={cn(
        'rounded-md outline-offset-2 transition-colors',
        canDrop && 'outline-dashed outline-1 outline-primary/50',
        isHighlighted && 'bg-primary/10 outline-2 outline-primary'
    )}
    ondragover={handleDragOver}
    ondragleave={handleDragLeave}
    ondrop={handleDrop}
>
    {@render children()}
</div>
