<script lang="ts">
    import { Trash2 } from '@lucide/svelte';

    const SIZE = 24;

    interface Props {
        bbox: { x: number; y: number; width: number; height: number };
        index: number;
        // Screen pixels per image pixel, so the button keeps its size when zooming.
        scale: number;
        disabled: boolean;
        onDelete: () => void;
    }

    let { bbox, index, scale, disabled, onDelete }: Props = $props();

    const x = $derived(Math.max(0, bbox.x + bbox.width - SIZE / scale));
    const y = $derived(Math.max(0, bbox.y - SIZE / scale));
</script>

<g transform={`translate(${x} ${y}) scale(${1 / scale})`}>
    <foreignObject width={SIZE} height={SIZE} pointer-events="all">
        <button
            type="button"
            class="flex size-6 items-center justify-center rounded-full bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90 disabled:opacity-50"
            aria-label={`Delete instance ${index + 1}`}
            title="Delete instance"
            {disabled}
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
</g>
