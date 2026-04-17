<script lang="ts">
    import { page } from '$app/state';
    import { onDestroy } from 'svelte';
    import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
    import {
        decodeRLEToBinaryMask,
        getImageCoordsFromMouse
    } from '$lib/components/SampleAnnotation/utils';
    import parseColor from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useAnnotationDeleteNavigation } from '$lib/hooks/useAnnotationDeleteNavigation/useAnnotationDeleteNavigation';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useInstanceSegmentationPreview } from '$lib/hooks/useInstanceSegmentationPreview';
    import { usePendingSaveTokens } from '$lib/hooks/usePendingSaveTokens/usePendingSaveTokens';
    import { useSegmentationMaskEraser } from '$lib/hooks/useSegmentationMaskEraser';
    import { addAnnotationDeleteToUndoStack } from '$lib/services/addAnnotationDeleteToUndoStack';
    import type { SavePendingChange } from '../savePendingChange';
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
        onFinishErasePendingChange?: (pendingChange: SavePendingChange) => void;
    };

    let {
        sample,
        interactionRect = $bindable<SVGRectElement>(),
        mousePosition,
        collectionId,
        brushRadius,
        drawerStrokeColor,
        refetch,
        onFinishErasePendingChange
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

    let baseMask = $state<Uint8Array | null>(null);
    let selectedAnnotation = $state<AnnotationView | null>(null);
    let lastBrushPoint = $state<{ x: number; y: number } | null>(null);
    let previewCanvas = $state<HTMLCanvasElement | null>(null);
    let isPreviewVisible = $state(false);

    // Parse the color once and cache it for direct mask rendering.
    const parsedColor = $derived(parseColor(drawerStrokeColor));

    // Hook owns mask drawing + preview composition.
    const previewApi = useInstanceSegmentationPreview({
        onPreviewVisibilityChange: (visible) => {
            isPreviewVisible = visible;
        }
    });

    $effect(() => {
        previewApi.setPreviewCanvas(previewCanvas);
    });

    const {
        startPending: startFinishErasePending,
        endPending: endFinishErasePending,
        resetPending: resetFinishErasePending
    } = usePendingSaveTokens({
        tokenPrefix: 'eraser',
        onPendingChange: (pendingChange: SavePendingChange) => {
            onFinishErasePendingChange?.(pendingChange);
        }
    });

    onDestroy(() => {
        resetFinishErasePending();
        setIsDrawing(false);
        previewApi.destroy();
    });

    const resetPreviewState = ({ clearDrawing = true }: { clearDrawing?: boolean } = {}) => {
        if (clearDrawing) {
            setIsDrawing(false);
        }

        lastBrushPoint = null;
        previewApi.cancelScheduledPreviewCompose();
        previewApi.clearPreview();
        isPreviewVisible = false;
    };

    $effect(() => {
        const annId = annotationLabelContext.annotationId;
        if (!annId) {
            resetPreviewState();
            baseMask = null;
            selectedAnnotation = null;
            return;
        }

        const ann = sample.annotations.find((a) => a.sample_id === annId);
        const rle = ann?.segmentation_details?.segmentation_mask;

        if (!rle) {
            toast.error('No segmentation mask to erase');
            resetPreviewState();
            baseMask = null;
            selectedAnnotation = null;
            return;
        }

        baseMask = decodeRLEToBinaryMask(rle, sample.width, sample.height);
        selectedAnnotation = ann;
        resetPreviewState();
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

    const releasePointerCapture = (e: PointerEvent) => {
        const pointerTarget = e.currentTarget as Element | null;
        pointerTarget?.releasePointerCapture?.(e.pointerId);
    };

    const handleStrokeComplete = (e: PointerEvent) => {
        releasePointerCapture(e);
        if (!annotationLabelContext.isDrawing) {
            resetPreviewState();
            return;
        }

        resetPreviewState({ clearDrawing: false });

        const updatedMask = previewApi.toBinaryMaskFromCanvas(sample.width, sample.height);
        if (!updatedMask) {
            setIsDrawing(false);
            return;
        }

        baseMask = updatedMask;
        const pendingToken = startFinishErasePending();
        setIsDrawing(false);
        void eraserApi
            .finishErase(updatedMask, selectedAnnotation, updateAnnotation, deleteAnn)
            .catch((error) => {
                console.error('Failed to finish erase stroke:', error);
            })
            .finally(() => {
                endFinishErasePending(pendingToken);
            });
    };

    const handleStrokeCancel = (e: PointerEvent) => {
        releasePointerCapture(e);
        resetPreviewState();
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
<foreignObject
    x="0"
    y="0"
    width={sample.width}
    height={sample.height}
    class:previewHidden={!isPreviewVisible}
>
    <canvas
        bind:this={previewCanvas}
        width={sample.width}
        height={sample.height}
        style="width: 100%; height: 100%; pointer-events: none; opacity: 0.85;"
    ></canvas>
</foreignObject>

<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor="crosshair"
    onpointerdown={(e) => {
        e.currentTarget?.setPointerCapture?.(e.pointerId);

        if (!annotationLabelContext.annotationId)
            return toast.error('No annotation selected for erasing');
        if (!baseMask) return;

        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);
        if (!point) return;

        setIsDrawing(true);
        lastBrushPoint = point;
        isPreviewVisible = false;
        previewApi.cancelScheduledPreviewCompose();
        previewApi.drawMaskToCanvas(baseMask, sample.width, sample.height);
        previewApi.drawBrushDot({
            point,
            brushRadius,
            width: sample.width,
            height: sample.height,
            compositeOperation: 'destination-out'
        });
        previewApi.schedulePreviewCompose({
            width: sample.width,
            height: sample.height,
            color: parsedColor,
            isDrawing: Boolean(annotationLabelContext.isDrawing)
        });
    }}
    onpointermove={(e) => {
        if (!annotationLabelContext.isDrawing) return;

        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);
        if (!point) return;

        if (lastBrushPoint) {
            previewApi.drawBrushLine({
                from: lastBrushPoint,
                to: point,
                brushRadius,
                width: sample.width,
                height: sample.height,
                compositeOperation: 'destination-out'
            });
            previewApi.drawBrushDot({
                point,
                brushRadius,
                width: sample.width,
                height: sample.height,
                compositeOperation: 'destination-out'
            });
        } else {
            previewApi.drawBrushDot({
                point,
                brushRadius,
                width: sample.width,
                height: sample.height,
                compositeOperation: 'destination-out'
            });
        }

        lastBrushPoint = point;
        previewApi.schedulePreviewCompose({
            width: sample.width,
            height: sample.height,
            color: parsedColor,
            isDrawing: Boolean(annotationLabelContext.isDrawing)
        });
    }}
    onpointerup={handleStrokeComplete}
    onpointercancel={handleStrokeCancel}
/>

<style>
    .previewHidden {
        visibility: hidden;
    }
</style>
