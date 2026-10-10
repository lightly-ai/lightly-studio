<script lang="ts">
    import type { NormalizedBox } from './annotationPreview.helpers';

    interface Props {
        box: NormalizedBox;
        image: { width: number; height: number };
        dashed?: boolean;
    }

    let { box, image, dashed = false }: Props = $props();
</script>

<rect
    x={box.x * image.width}
    y={box.y * image.height}
    width={box.width * image.width}
    height={box.height * image.height}
    fill="rgba(59, 130, 246, 0.15)"
    stroke="#93c5fd"
    stroke-width="2"
    stroke-dasharray={dashed ? '6 5' : undefined}
    vector-effect="non-scaling-stroke"
    pointer-events="none"
/>
