<script lang="ts">
    import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';

    const FONT_SIZE = 12;
    const PADDING = 3;
    const SCORE_TO_PERCENT = 100;

    interface Props {
        preview: Pick<ModelAnnotationPreview, 'bbox' | 'class_name' | 'score'>;
        // Screen pixels per image pixel, so the tag keeps its size when zooming.
        scale: number;
    }

    let { preview, scale }: Props = $props();

    const text = $derived(`${preview.class_name} ${Math.round(preview.score * SCORE_TO_PERCENT)}%`);
</script>

<!-- Inside the top-left corner, as the delete button is above the top-right corner. -->
<g
    transform={`translate(${preview.bbox.x} ${preview.bbox.y}) scale(${1 / scale})`}
    pointer-events="none"
    data-testid="preview-class-tag"
>
    <!-- An outline, not a background box, as the text width is not known before layout. -->
    <text
        x={PADDING}
        y={FONT_SIZE + PADDING}
        font-size={FONT_SIZE}
        font-weight="600"
        fill="white"
        stroke="#16a34a"
        stroke-width="4"
        stroke-linejoin="round"
        paint-order="stroke">{text}</text
    >
</g>
