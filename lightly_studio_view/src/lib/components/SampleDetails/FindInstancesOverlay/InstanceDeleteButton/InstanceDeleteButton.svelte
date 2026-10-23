<script lang="ts">
    import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
    import { Trash2 } from '@lucide/svelte';

    const SIZE = 24;
    const ICON_SIZE = 14;

    interface Props {
        bbox: AnnotationPreview['bbox'];
        index: number;
        // Screen pixels per image pixel, so the button keeps its size when zooming.
        scale: number;
        disabled: boolean;
        onDelete: () => void;
    }

    let { bbox, index, scale, disabled, onDelete }: Props = $props();

    const x = $derived(Math.max(0, bbox.x + bbox.width - SIZE / scale));
    const y = $derived(Math.max(0, bbox.y - SIZE / scale));

    const onKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        if (!disabled) onDelete();
    };
</script>

<!-- Plain SVG, as WebKit misplaces styled HTML in a scaled foreignObject. -->
<g
    transform={`translate(${x} ${y}) scale(${1 / scale})`}
    role="button"
    tabindex={disabled ? -1 : 0}
    aria-label={`Delete instance ${index + 1}`}
    aria-disabled={disabled}
    opacity={disabled ? 0.5 : 1}
    pointer-events="all"
    class={disabled ? 'cursor-not-allowed' : 'group cursor-pointer'}
    onclick={(event) => {
        event.stopPropagation();
        if (!disabled) onDelete();
    }}
    onkeydown={onKeyDown}
    onpointerdown={(event) => event.stopPropagation()}
    onmousedown={(event) => event.stopPropagation()}
>
    <title>Delete instance</title>
    <circle
        cx={SIZE / 2}
        cy={SIZE / 2}
        r={SIZE / 2}
        class="fill-destructive group-hover:fill-destructive/90"
    />
    <Trash2
        x={(SIZE - ICON_SIZE) / 2}
        y={(SIZE - ICON_SIZE) / 2}
        size={ICON_SIZE}
        class="text-destructive-foreground"
    />
</g>
