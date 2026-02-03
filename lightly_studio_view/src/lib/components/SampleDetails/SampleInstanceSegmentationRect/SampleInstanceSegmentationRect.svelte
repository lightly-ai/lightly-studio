<script lang="ts">
    import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
    import {
        applyBrushToMask,
        decodeRLEToBinaryMask,
        getImageCoordsFromMouse,
        interpolateLineBetweenPoints,
        maskToDataUrl,
        withAlpha
    } from '$lib/components/SampleAnnotation/utils';
    import parseColor from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useInstanceSegmentationBrush } from '$lib/hooks/useInstanceSegmentationBrush';
    import { useCollectionWithChildren } from '$lib/hooks/useCollection/useCollection';
    import { page } from '$app/state';
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
    const datasetId = $derived(page.params.dataset_id!);
    const { refetch: refetchRootCollection } = $derived.by(() =>
        useCollectionWithChildren({ collectionId: datasetId })
    );
    const { finishBrush } = useInstanceSegmentationBrush({
        collectionId,
        sampleId,
        sample,
        refetch,
        onAnnotationCreated: () => {
            // Only refresh root collection if there were no annotations before
            if (sample.annotations.length === 0) {
                refetchRootCollection();
            }
        }
    });

    const { context: annotationLabelContext, setIsDrawing } = useAnnotationLabelContext();

    let brushPath = $state<{ x: number; y: number }[]>([]);
    let workingMask = $state<Uint8Array | null>(null);
    let selectedAnnotation = $state<AnnotationView | null>(null);
    let lastBrushPoint = $state<{ x: number; y: number } | null>(null);

    // Parse the color once and cache it for direct mask rendering.
    const parsedColor = $derived(parseColor(drawerStrokeColor));

    $effect(() => {
        if (!annotationLabelContext.annotationId) {
            selectedAnnotation = null;
            workingMask = null;
            brushPath = [];
            return;
        }

        const ann = sample.annotations?.find(
            (a) => a.sample_id === annotationLabelContext.annotationId
        );

        const rle = ann?.segmentation_details?.segmentation_mask;
        if (!ann) {
            workingMask = new Uint8Array(sample.width * sample.height);
            selectedAnnotation = null;
            return;
        }

        if (!rle) {
            workingMask = new Uint8Array(sample.width * sample.height);
            selectedAnnotation = ann;
            return;
        }

        workingMask = decodeRLEToBinaryMask(rle, sample.width, sample.height);
        selectedAnnotation = ann;
    });

    const updateAnnotation = async (input: AnnotationUpdateInput) => {
        await annotationApi?.updateAnnotation(input);
        refetch();
    };
</script>

{#if mousePosition}
    <circle
        cx={mousePosition.x}
        cy={mousePosition.y}
        r={brushRadius}
        fill={withAlpha(drawerStrokeColor, 0.25)}
    />
{/if}
{#if workingMask && annotationLabelContext.isDrawing}
    <image
        href={maskToDataUrl(workingMask, sample.width, sample.height, parsedColor)}
        width={sample.width}
        height={sample.height}
        opacity={0.85}
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

        if (lastBrushPoint) {
            const interpolatedPoints = interpolateLineBetweenPoints(lastBrushPoint, point);
            applyBrushToMask(
                workingMask,
                sample.width,
                sample.height,
                interpolatedPoints,
                brushRadius,
                1
            );
            brushPath = [...brushPath, ...interpolatedPoints];
        } else {
            applyBrushToMask(workingMask, sample.width, sample.height, [point], brushRadius, 1);
            brushPath = [...brushPath, point];
        }

        lastBrushPoint = point;
    }}
    onpointerleave={() => {
        lastBrushPoint = null;
        finishBrush(workingMask, selectedAnnotation, $labels.data ?? [], updateAnnotation);
    }}
    onpointerup={() => {
        lastBrushPoint = null;
        finishBrush(workingMask, selectedAnnotation, $labels.data ?? [], updateAnnotation);
    }}
    onpointerdown={(e) => {
        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);
        if (!point) return;

        setIsDrawing(true);
        lastBrushPoint = point;
        brushPath = [point];

        if (!workingMask) {
            workingMask = new Uint8Array(sample.width * sample.height);
        }

        applyBrushToMask(workingMask, sample.width, sample.height, [point], brushRadius, 1);
    }}
/>
