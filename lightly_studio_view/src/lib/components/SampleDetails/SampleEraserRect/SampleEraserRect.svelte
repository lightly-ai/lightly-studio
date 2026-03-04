<script lang="ts">
    import { page } from '$app/state';
    import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
    import {
        applyBrushToMask,
        decodeRLEToBinaryMask,
        getImageCoordsFromMouse,
        interpolateLineBetweenPoints,
        maskToDataUrl
    } from '$lib/components/SampleAnnotation/utils';
    import parseColor from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useAnnotationDeleteNavigation } from '$lib/hooks/useAnnotationDeleteNavigation/useAnnotationDeleteNavigation';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useSegmentationMaskEraser } from '$lib/hooks/useSegmentationMaskEraser';
    import { addAnnotationDeleteToUndoStack } from '$lib/services/addAnnotationDeleteToUndoStack';
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

    const {
        context: annotationLabelContext,
        setIsDrawing,
        setAnnotationId
    } = useAnnotationLabelContext();

    const { deleteAnnotation } = useDeleteAnnotation({
        collectionId
    });
    const annotationLabels = useAnnotationLabels({ collectionId });
    const { addReversibleAction } = useGlobalStorage();
    const { createAnnotation } = useCreateAnnotation({
        collectionId
    });
    const eraserApi = $derived.by(() =>
        useSegmentationMaskEraser({
            collectionId,
            sample,
            refetch: annotationLabelContext.isOnAnnotationDetailsView ? undefined : refetch
        })
    );

    const annotationApi = $derived.by(() => {
        if (!annotationLabelContext.annotationId) return null;
        return useAnnotation({
            collectionId,
            annotationId: annotationLabelContext.annotationId
        });
    });

    let workingMask = $state<Uint8Array | null>(null);
    let selectedAnnotation = $state<AnnotationView | null>(null);
    let lastBrushPoint = $state<{ x: number; y: number } | null>(null);
    let previewDataUrl = $state<string>('');

    // Parse the color once and cache it for direct mask rendering.
    const parsedColor = $derived(parseColor(drawerStrokeColor));

    const updatePreview = () => {
        if (!workingMask) return;
        previewDataUrl = maskToDataUrl(workingMask, sample.width, sample.height, parsedColor);
    };

    $effect(() => {
        const annId = annotationLabelContext.annotationId;
        if (!annId) {
            workingMask = null;
            previewDataUrl = '';
            return;
        }

        const ann = sample.annotations.find((a) => a.sample_id === annId);
        const rle = ann?.segmentation_details?.segmentation_mask;

        if (!rle) {
            toast.error('No segmentation mask to erase');
            workingMask = null;
            previewDataUrl = '';
            selectedAnnotation = null;
            return;
        }

        workingMask = decodeRLEToBinaryMask(rle, sample.width, sample.height);
        selectedAnnotation = ann;
        previewDataUrl = '';
    });

    const updateAnnotation = async (input: AnnotationUpdateInput) => {
        await annotationApi?.updateAnnotation(input);
        refetch();
    };

    const datasetId = $derived(page.params.dataset_id);
    const collectionType = $derived(page.params.collection_type ?? page.data.collectionType);
    const currentAnnotationId = $derived(
        annotationLabelContext.annotationId ?? sample.annotations[0]?.sample_id ?? ''
    );

    const { gotoNextAnnotation } = $derived.by(() =>
        useAnnotationDeleteNavigation({
            annotationId: currentAnnotationId,
            collectionId,
            datasetId,
            collectionType
        })
    );

    async function deleteAnn() {
        const labels = $annotationLabels.data;

        const annotation = sample.annotations.find(
            (a) => a.sample_id === annotationLabelContext.annotationId
        );

        if (!(annotation || labels)) return;

        try {
            addAnnotationDeleteToUndoStack({
                annotation: annotation!,
                labels: labels!,
                addReversibleAction,
                createAnnotation,
                refetch
            });

            await deleteAnnotation(annotation!.sample_id);
            toast.success('Annotation deleted successfully');

            if (annotationLabelContext.isOnAnnotationDetailsView) return gotoNextAnnotation();

            refetch();
            setAnnotationId(null);
        } catch (error) {
            toast.error('Failed to delete annotation. Please try again.');
            console.error('Error deleting annotation:', error);
        }
    }
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
{#if previewDataUrl && annotationLabelContext.isDrawing}
    <image href={previewDataUrl} width={sample.width} height={sample.height} opacity={0.85} />
{/if}

<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor="crosshair"
    onpointerdown={(e) => {
        e.currentTarget?.setPointerCapture?.(e.pointerId);

        if (!annotationLabelContext.annotationId)
            return toast.error('No annotation selected for erasing');
        if (!workingMask) return;

        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);
        if (!point) return;

        setIsDrawing(true);
        lastBrushPoint = point;

        applyBrushToMask(workingMask, sample.width, sample.height, [point], brushRadius, 0);
        updatePreview();
    }}
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
                0
            );
        } else {
            applyBrushToMask(workingMask, sample.width, sample.height, [point], brushRadius, 0);
        }

        lastBrushPoint = point;
        updatePreview();
    }}
    onpointerup={(e) => {
        e.currentTarget?.releasePointerCapture?.(e.pointerId);

        lastBrushPoint = null;
        eraserApi.finishErase(workingMask, selectedAnnotation, updateAnnotation, deleteAnn);
    }}
/>
