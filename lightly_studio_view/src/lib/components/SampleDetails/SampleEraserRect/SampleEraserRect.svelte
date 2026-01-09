<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import {
        applyBrushToMask,
        computeBoundingBoxFromMask,
        decodeRLEToBinaryMask,
        encodeBinaryMaskToRLE,
        getImageCoordsFromMouse
    } from '$lib/components/SampleAnnotation/utils';
    import { toast } from 'svelte-sonner';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    type SampleEraserRectProps = {
        sample: {
            width: number;
            height: number;
            annotations: AnnotationView[];
        };
        interactionRect?: SVGRectElement | undefined | null;
        collectionId: string;
        brushRadius: number;
        selectedAnnotationId: string | null | undefined;
        refetch: () => void;
    };

    let {
        sample,
        interactionRect = $bindable<SVGRectElement>(),
        collectionId,
        selectedAnnotationId,
        brushRadius,
        refetch
    }: SampleEraserRectProps = $props();

    let eraserPath = $state<{ x: number; y: number }[]>([]);

    const { updateAnnotation } = $derived(
        useAnnotation({
            collectionId,
            annotationId: selectedAnnotationId!
        })
    );

    let decodedMasks = new Map<string, Uint8Array>();

    // Populate the decoded masks with the annotations insance segmentation details.
    $effect(() => {
        decodedMasks.clear();

        for (const ann of sample.annotations ?? []) {
            const rle = ann.instance_segmentation_details?.segmentation_mask;
            if (!rle) continue;

            decodedMasks.set(
                ann.sample_id,
                decodeRLEToBinaryMask(rle, sample.width, sample.height)
            );
        }
    });

    const findAnnotationAtPoint = (x: number, y: number): string | null => {
        const ix = Math.round(x);
        const iy = Math.round(y);
        const w = sample.width;
        const idx = iy * w + ix;

        // Iterate in reverse draw order
        const anns = [...(sample.annotations ?? [])].reverse();

        for (const ann of anns) {
            const mask = decodedMasks.get(ann.sample_id);
            if (!mask) continue;

            if (mask[idx] === 1) {
                return ann.sample_id;
            }
        }

        return null;
    };

    const finishEraser = async () => {
        annotationLabelContext.isErasing = false;

        if (!selectedAnnotationId) {
            return toast.info('Please, select an annotation first.');
        }

        if (eraserPath.length === 0) {
            eraserPath = [];
            return;
        }

        const annotation = sample.annotations?.find((a) => a.sample_id === selectedAnnotationId);
        const rle = annotation?.instance_segmentation_details?.segmentation_mask;
        if (!rle) {
            toast.error('No segmentation mask to edit');
            eraserPath = [];
            return;
        }

        const imageWidth = sample.width;
        const imageHeight = sample.height;

        // Decode
        const mask = decodeRLEToBinaryMask(rle, imageWidth, imageHeight);

        const writeValue: 0 | 1 = 0;
        applyBrushToMask(mask, imageWidth, imageHeight, eraserPath, brushRadius, writeValue);

        // Recompute bbox
        const bbox = computeBoundingBoxFromMask(mask, imageWidth, imageHeight);
        eraserPath = [];

        const newRLE = encodeBinaryMaskToRLE(mask);

        await updateAnnotation({
            annotation_id: selectedAnnotationId,
            collection_id: collectionId,
            segmentation_mask: newRLE,
            bounding_box: bbox
        });

        refetch();
        eraserPath = [];
    };

    const annotationLabelContext = useAnnotationLabelContext();
</script>

{#if eraserPath.length}
    <circle
        cx={eraserPath[eraserPath.length - 1].x}
        cy={eraserPath[eraserPath.length - 1].y}
        r={brushRadius}
        fill="rgba(255,255,255,0.2)"
        stroke="white"
    />
{/if}
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor={'auto'}
    onpointerdown={(e) => {
        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);
        if (!point) return;

        annotationLabelContext.isErasing = true;

        const hitAnnotationId = findAnnotationAtPoint(point.x, point.y);
        if (!hitAnnotationId) return;

        selectedAnnotationId = hitAnnotationId;
        eraserPath = [point];
    }}
    onpointermove={(e) => {
        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);

        if (point) eraserPath = [...eraserPath, point];
    }}
    onpointerup={finishEraser}
    onmouseleave={finishEraser}
/>
