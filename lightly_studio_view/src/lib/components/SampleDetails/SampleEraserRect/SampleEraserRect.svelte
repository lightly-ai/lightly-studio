<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { SampleAnnotationSegmentationRLE } from '$lib/components';
    import {
        applyBrushToMask,
        computeBoundingBoxFromMask,
        decodeRLEToBinaryMask,
        encodeBinaryMaskToRLE,
        getImageCoordsFromMouse,
        withAlpha
    } from '$lib/components/SampleAnnotation/utils';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import type { BoundingBox } from '$lib/types';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';
    import { toast } from 'svelte-sonner';

    type Props = {
        sample: {
            width: number;
            height: number;
            annotations: AnnotationView[];
        };
        interactionRect?: SVGRectElement | null;
        mousePosition: { x: number; y: number } | null;
        collectionId: string;
        brushRadius: number;
        drawerStrokeColor: string;
        refetch: () => void;
    };

    let {
        sample,
        interactionRect = $bindable<SVGRectElement>(),
        mousePosition,
        collectionId,
        brushRadius,
        drawerStrokeColor,
        refetch
    }: Props = $props();

    const annotationLabelContext = useAnnotationLabelContext();

    const annotationApi = $derived.by(() => {
        if (!annotationLabelContext.annotationId) return null;
        return useAnnotation({
            collectionId,
            annotationId: annotationLabelContext.annotationId
        });
    });

    let workingMask = $state<Uint8Array | null>(null);
    let previewRLE = $state<number[]>([]);

    $effect(() => {
        annotationLabelContext.isDrawing = false;
        const annId = annotationLabelContext.annotationId;
        if (!annId) {
            workingMask = null;
            previewRLE = [];
            return;
        }

        const ann = sample.annotations.find((a) => a.sample_id === annId);
        const rle = ann?.instance_segmentation_details?.segmentation_mask;

        if (!rle) {
            toast.error('No segmentation mask to erase');
            workingMask = null;
            previewRLE = [];
            return;
        }

        workingMask = decodeRLEToBinaryMask(rle, sample.width, sample.height);

        previewRLE = rle;
    });

    const updatePreview = () => {
        if (!workingMask) return;
        previewRLE = encodeBinaryMaskToRLE(workingMask);
    };

    const finishErase = async () => {
        if (!annotationLabelContext.isDrawing || !workingMask) {
            annotationLabelContext.isDrawing = false;
            return;
        }

        const bbox = computeBoundingBoxFromMask(workingMask, sample.width, sample.height);

        if (!bbox) {
            toast.error('Segmentation became empty');
            previewRLE = [];
            return;
        }

        const rle = encodeBinaryMaskToRLE(workingMask);

        try {
            await annotationApi?.updateAnnotation({
                annotation_id: annotationLabelContext.annotationId!,
                collection_id: collectionId,
                bounding_box: bbox,
                segmentation_mask: rle
            });
        } catch (err) {
            console.error(err);
            toast.error('Failed to update segmentation');
        }

        refetch();
    };
</script>

{#if mousePosition}
    <circle
        cx={mousePosition.x}
        cy={mousePosition.y}
        r={brushRadius}
        fill="rgba(255, 255, 255, 0.15)"
        stroke="white"
        stroke-width="1"
        pointer-events="none"
    />
{/if}
{#if previewRLE.length > 0}
    <SampleAnnotationSegmentationRLE
        segmentation={previewRLE}
        width={sample.width}
        colorFill={withAlpha(drawerStrokeColor, 0.5)}
    />
{/if}

<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor="crosshair"
    onpointerdown={(e) => {
        if (!annotationLabelContext.annotationId)
            return toast.error('No annotation selected for erasing');
        if (!workingMask) return;

        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);
        if (!point) return;

        annotationLabelContext.isDrawing = true;

        applyBrushToMask(workingMask, sample.width, sample.height, [point], brushRadius, 0);

        updatePreview();
    }}
    onpointermove={(e) => {
        if (!annotationLabelContext.isDrawing || !workingMask) return;

        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);
        if (!point) return;
        annotationLabelContext.isDrawing = true;
        applyBrushToMask(workingMask, sample.width, sample.height, [point], brushRadius, 0);

        updatePreview();
    }}
    onpointerup={finishErase}
    onpointerleave={finishErase}
/>
