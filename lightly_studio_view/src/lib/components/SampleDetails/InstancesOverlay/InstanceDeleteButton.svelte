<script lang="ts">
    import { Trash2 } from '@lucide/svelte';

    interface Props {
        bbox: { x: number; y: number; width: number; height: number };
        index: number;
        onDelete: () => void;
    }

    let { bbox, index, onDelete }: Props = $props();
</script>

<foreignObject
    x={Math.max(0, bbox.x + bbox.width - 24)}
    y={Math.max(0, bbox.y - 24)}
    width="24"
    height="24"
    pointer-events="all"
>
    <button
        type="button"
        class="flex size-6 items-center justify-center rounded-full bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90"
        aria-label={`Delete instance ${index + 1}`}
        title="Delete instance"
        onclick={(event) => {
            event.stopPropagation();
            onDelete();
        }}
        onpointerdown={(event) => event.stopPropagation()}
        onmousedown={(event) => event.stopPropagation()}
    >
        <Trash2 class="size-3.5" />
    </button>
</foreignObject>
