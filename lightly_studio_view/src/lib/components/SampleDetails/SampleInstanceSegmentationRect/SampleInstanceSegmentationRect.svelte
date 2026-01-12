<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { SampleAnnotationSegmentationRLE } from '$lib/components';
    import {
        applyBrushToMask,
        decodeRLEToBinaryMask,
        encodeBinaryMaskToRLE,
        getImageCoordsFromMouse,
        withAlpha
    } from '$lib/components/SampleAnnotation/utils';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useInstanceSegmentationBrush } from '$lib/hooks/useInstanceSegmentationBrush';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';

    type SampleInstanceSegmentationRectProps = {
        sample: {
            width: number;
            height: number;
            annotations: AnnotationView[];
        };
        interactionRect?: SVGRectElement | undefined | null;
        mousePosition: { x: number; y: number } | null;
        sampleId: string;
        collectionId: string;
        brushRadius: number;
        drawerStrokeColor: string;
        annotationLabel?: string | null | undefined;
        refetch: () => void;
    };

    let {
        sample,
        interactionRect = $bindable<SVGRectElement>(),
        sampleId,
        collectionId,
        brushRadius,
        drawerStrokeColor,
        mousePosition,
        refetch
    }: SampleInstanceSegmentationRectProps = $props();

    const labels = useAnnotationLabels({ collectionId });
    const annotationApi = $derived.by(() => {
        if (!annotationLabelContext.annotationId) return null;

        return useAnnotation({
            collectionId,
            annotationId: annotationLabelContext.annotationId!
        });
    });
    const { finishBrush } = useInstanceSegmentationBrush({
        collectionId,
        sampleId,
        sample,
        labels: $labels.data ?? [],
        refetch
    });

    const annotationLabelContext = useAnnotationLabelContext();

    let brushPath = $state<{ x: number; y: number }[]>([]);
    let workingMask = $state<Uint8Array | null>(null);
    let previewRLE = $state<number[]>([]);
    let selectedAnnotation = $state<AnnotationView | null>(null);

    $effect(() => {
        if (annotationLabelContext.isDrawing) return;

        if (!annotationLabelContext.annotationId) {
            previewRLE = [];
            selectedAnnotation = null;
            workingMask = null;
            brushPath = [];
            return;
        }

        const ann = sample.annotations?.find(
            (a) => a.sample_id === annotationLabelContext.annotationId
        );

        const rle = ann?.instance_segmentation_details?.segmentation_mask;
        if (!rle) {
            workingMask = new Uint8Array(sample.width * sample.height);
            previewRLE = [];
            selectedAnnotation = null;
            return;
        }

        workingMask = decodeRLEToBinaryMask(rle, sample.width, sample.height);
        selectedAnnotation = ann;
        previewRLE = rle;
    });

    const updatePreview = () => {
        if (!workingMask) return;
        previewRLE = encodeBinaryMaskToRLE(workingMask);
    };
</script>

{#if mousePosition}
    <circle
        cx={mousePosition.x}
        cy={mousePosition.y}
        r={brushRadius}
        fill={withAlpha(drawerStrokeColor, 0.2)}
    />
{/if}
{#if previewRLE.length > 0 && annotationLabelContext.isDrawing}
    <SampleAnnotationSegmentationRLE
        segmentation={previewRLE}
        width={sample.width}
        colorFill={withAlpha(drawerStrokeColor, 0.4)}
        opacity={0.65}
    />
{/if}
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor={'crosshair'}
    onpointermove={(e) => {
        if (!annotationLabelContext.isDrawing || !workingMask) return;

        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);
        if (!point) return;

        brushPath = [...brushPath, point];

        applyBrushToMask(workingMask, sample.width, sample.height, [point], brushRadius, 1);
        updatePreview();
    }}
    onpointerleave={() =>
        finishBrush(workingMask, selectedAnnotation, annotationApi?.updateAnnotation)}
    onpointerup={() =>
        finishBrush(workingMask, selectedAnnotation, annotationApi?.updateAnnotation)}
    onpointerdown={(e) => {
        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);
        if (!point) return;

        annotationLabelContext.isDrawing = true;
        brushPath.push(point);

        if (!workingMask) {
            workingMask = new Uint8Array(sample.width * sample.height);
        }

        applyBrushToMask(workingMask, sample.width, sample.height, [point], brushRadius, 1);
        updatePreview();
    }}
/>
