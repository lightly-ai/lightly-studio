<script lang="ts">
    import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
    import SampleAnnotationSegmentationRLE from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/SampleAnnotationSegmentationRLE.svelte';
    import type { OutputType } from './annotationPreview.helpers';

    interface Props {
        preview: Pick<AnnotationPreview, 'bbox' | 'segmentation_mask'>;
        outputType: OutputType;
    }

    let { preview, outputType }: Props = $props();
</script>

<g pointer-events="none" data-testid="annotation-preview">
    {#if outputType === 'mask'}
        <g transform={`translate(${preview.bbox.x} ${preview.bbox.y})`}>
            <SampleAnnotationSegmentationRLE
                width={preview.bbox.width}
                segmentation={preview.segmentation_mask}
                colorFill="rgba(34, 197, 94, 0.55)"
                opacity={0.85}
            />
        </g>
    {/if}
    <rect
        x={preview.bbox.x}
        y={preview.bbox.y}
        width={preview.bbox.width}
        height={preview.bbox.height}
        fill="none"
        stroke="#86efac"
        stroke-width="2"
        stroke-linejoin="round"
        stroke-dasharray="6 5"
        vector-effect="non-scaling-stroke"
    />
</g>
