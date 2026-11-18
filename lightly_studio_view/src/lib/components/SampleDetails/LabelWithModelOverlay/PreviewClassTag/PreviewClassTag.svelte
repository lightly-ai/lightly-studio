<script lang="ts">
    import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';

    const FONT_SIZE = 12;
    const PADDING = 3;

    interface Props {
        preview: Pick<ModelAnnotationPreview, 'bbox' | 'class_name' | 'score'>;
        // Screen pixels per image pixel, so the tag keeps its size when zooming.
        scale: number;
        color?: string;
    }

    let { preview, scale, color = '#16a34a' }: Props = $props();

    const text = $derived(`${preview.class_name} ${Math.round(preview.score * 100)}%`);
    const height = FONT_SIZE + 2 * PADDING;
</script>

<!-- Inside the top-left corner, as the delete button is above the top-right corner. -->
<g
    transform={`translate(${preview.bbox.x} ${preview.bbox.y}) scale(${1 / scale})`}
    pointer-events="none"
    data-testid="preview-class-tag"
>
    <rect width={text.length * FONT_SIZE * 0.6 + 2 * PADDING} {height} rx="2" fill={color} />
    <text x={PADDING} y={FONT_SIZE} font-size={FONT_SIZE} fill="white">{text}</text>
</g>
