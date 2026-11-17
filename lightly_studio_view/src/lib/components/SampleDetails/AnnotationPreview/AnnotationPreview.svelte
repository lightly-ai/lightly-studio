<script lang="ts">
    import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
    import SampleAnnotationSegmentationRLE from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/SampleAnnotationSegmentationRLE.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { getPreviewMaskOpacity } from '../previewMaskOpacity';

    interface Props {
        // A null mask shows only the box, e.g. for an object detection model.
        preview: Pick<AnnotationPreview, 'bbox'> & {
            segmentation_mask: AnnotationPreview['segmentation_mask'] | null;
        };
        image: { width: number };
        saveAs: 'mask' | 'box';
        colorStroke?: string;
        colorFill?: string;
        strokeDasharray?: string;
    }

    let {
        preview,
        image,
        saveAs,
        colorStroke = '#86efac',
        colorFill = 'rgba(34, 197, 94, 0.55)',
        strokeDasharray = '6 5'
    }: Props = $props();

    const { maskOpacity } = useGlobalStorage();
</script>

<g pointer-events="none" data-testid="annotation-preview">
    {#if saveAs === 'mask' && preview.segmentation_mask}
        <SampleAnnotationSegmentationRLE
            width={image.width}
            segmentation={preview.segmentation_mask}
            {colorFill}
            opacity={getPreviewMaskOpacity({ maskOpacity: $maskOpacity })}
        />
    {/if}
    <rect
        x={preview.bbox.x}
        y={preview.bbox.y}
        width={preview.bbox.width}
        height={preview.bbox.height}
        fill="none"
        stroke={colorStroke}
        stroke-width="2"
        stroke-linejoin="round"
        stroke-dasharray={strokeDasharray}
        vector-effect="non-scaling-stroke"
    />
</g>
