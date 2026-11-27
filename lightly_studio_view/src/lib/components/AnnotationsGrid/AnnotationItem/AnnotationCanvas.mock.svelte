<script lang="ts">
    import type { SourceCrop } from '$lib/workers/maskRendererUtils';

    interface CanvasAnnotation {
        annotation_type?: string;
        polygons?: Array<Array<[number, number]>>;
        color?: string;
        opacity?: number;
    }

    interface Props {
        outputWidth: number;
        outputHeight: number;
        objectFit: 'contain' | 'cover';
        sourceCrop?: SourceCrop;
        annotations?: CanvasAnnotation[];
    }

    let { outputWidth, outputHeight, objectFit, sourceCrop, annotations = [] }: Props = $props();
</script>

<div
    data-testid="mock-annotation-canvas"
    data-output-width={outputWidth}
    data-output-height={outputHeight}
    data-object-fit={objectFit}
    data-source-crop={JSON.stringify(sourceCrop)}
    data-annotation-type={annotations[0]?.annotation_type}
    data-polygons={JSON.stringify(annotations[0]?.polygons)}
    data-color={annotations[0]?.color}
    data-opacity={annotations[0]?.opacity}
></div>
