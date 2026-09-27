import { onDestroy, untrack } from 'svelte';
import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
import { getImageCoordsFromMouse } from '$lib/components/SampleAnnotation/utils';
import { toast } from 'svelte-sonner';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
import {
    useAnnotation,
    useAnnotationLabels,
    useCollectionWithChildren,
    useDeleteAnnotation,
    usePendingOperations,
    useSegmentationMaskBrush,
    useSelectClassDialog
} from '$lib/hooks';
import { useSlicResult } from './useSlicResult.svelte';
import { useSlicPreview } from './useSlicPreview.svelte';
import type { SuperpixelMaskEditor, SuperpixelStrokePreview } from '@lightly-ai/slic';
import { createSlicMaskEditor } from './createSlicMaskEditor';
import { createSlicStroke } from './createSlicStroke';
import { page } from '$app/state';
import type { PendingChange } from '../pendingChange';

interface SampleSlicRectProps {
    sample: {
        width: number;
        height: number;
        annotations: AnnotationView[];
    };
    interactionRect?: SVGRectElement | undefined | null;
    sampleId: string;
    collectionId: string;
    drawerStrokeColor: string;
    imageUrl: string;
    refetch: () => void;
    onFinishBrushPendingChange?: (pendingChange: PendingChange) => void;
}

export function useSlicInteraction(getProps: () => SampleSlicRectProps) {
    const {
        sample,
        interactionRect,
        sampleId,
        collectionId,
        drawerStrokeColor,
        imageUrl,
        refetch,
        onFinishBrushPendingChange
    } = $derived(getProps());

    const labels = useAnnotationLabels(() => ({ collectionId }));
    const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId: () => collectionId });
    const {
        open: selectClassDialogOpen,
        requestLabel,
        handleConfirm: handleSelectClassDialogConfirm,
        handleCancel: handleSelectClassDialogCancel
    } = useSelectClassDialog();
    const datasetId = $derived(page.params.dataset_id!);
    const { refetch: refetchRootCollection } = useCollectionWithChildren({
        getCollectionId: () => datasetId
    });
    const {
        context: annotationLabelContext,
        setAnnotationId,
        setIsDrawing
    } = useAnnotationLabelContext();
    const { context: toolbarContext, setSlicStatus } = useSampleDetailsToolbarContext();

    const activeAnnotationId = $derived.by(() => {
        if (annotationLabelContext.annotationId) return annotationLabelContext.annotationId;
        if (annotationLabelContext.isOnAnnotationDetailsView) {
            return sample.annotations[0]?.sample_id ?? null;
        }
        return null;
    });
    const annotationApi = useAnnotation(() => ({
        collectionId,
        annotationId: activeAnnotationId ?? '',
        enabled: !!activeAnnotationId
    }));
    const brushApi = $derived.by(() =>
        useSegmentationMaskBrush({
            collectionId,
            datasetId,
            sampleId,
            sample,
            annotations: sample.annotations,
            refetch,
            deleteAnnotation,
            requestLabel,
            onAnnotationCreated: () => {
                if (sample.annotations.length === 0) refetchRootCollection();
            }
        })
    );

    const {
        startPending: startFinishBrushPending,
        endPending: endFinishBrushPending,
        resetPending: resetFinishBrushPending
    } = usePendingOperations({
        operationPrefix: 'slic',
        onPendingChange: (pendingChange) => onFinishBrushPendingChange?.(pendingChange)
    });

    const slic = useSlicResult(() => ({
        imageUrl,
        level: toolbarContext.slic.level,
        color: drawerStrokeColor
    }));
    const slicResult = $derived(slic.result);
    let selectedAnnotation = $state<AnnotationView | null>(null);
    let isStrokeActive = $state(false);
    let isPersisting = $state(false);
    let editor: SuperpixelMaskEditor | null = null;
    const preview = useSlicPreview(() => ({
        width: slicResult?.segmentation.width ?? 0,
        height: slicResult?.segmentation.height ?? 0,
        color: drawerStrokeColor
    }));
    const stroke = createSlicStroke({
        getEditor: () => editor,
        onActiveChange: (active) => {
            isStrokeActive = active;
        }
    });
    const clearPreview = () => {
        preview.clear();
        stroke.cancel();
    };
    const renderStrokePreview = (stroke: SuperpixelStrokePreview) => {
        if (slicResult) preview.renderStroke(stroke.mask);
    };
    const updateHover = (point: { x: number; y: number } | null) => {
        if (point && editor && slicResult) preview.updateHover(point, editor);
    };

    const releasePointerCapture = (event: PointerEvent) => {
        const target = event.currentTarget as Element | null;
        if (target?.hasPointerCapture?.(event.pointerId))
            target.releasePointerCapture(event.pointerId);
    };

    const finishStroke = (event: PointerEvent) => {
        releasePointerCapture(event);
        if (!isStrokeActive) return;

        preview.clearStroke();
        const mask = stroke.commit();
        if (!mask) {
            setIsDrawing(false);
            return;
        }

        const pendingOperation = startFinishBrushPending();
        isPersisting = true;
        void (async () => {
            try {
                await brushApi.finishBrush(
                    mask,
                    selectedAnnotation,
                    labels.data ?? [],
                    async (input: AnnotationUpdateInput) => {
                        await annotationApi.updateAnnotation(input);
                    },
                    annotationLabelContext.lockedAnnotationIds
                );
            } catch {
                toast.error('Could not save the segmentation annotation');
            } finally {
                isPersisting = false;
                endFinishBrushPending(pendingOperation);
            }
        })();
    };

    onDestroy(() => {
        handleSelectClassDialogCancel();
        resetFinishBrushPending();
        setIsDrawing(false);
    });

    $effect(() => {
        setSlicStatus(slic.status);
        if (slicResult) return;
        untrack(() => {
            clearPreview();
            setIsDrawing(false);
            editor = null;
        });
    });

    $effect(() => {
        if (!slicResult || isStrokeActive || isPersisting) return;

        const nextSelectedAnnotation = activeAnnotationId
            ? (sample.annotations.find(
                  (annotation) => annotation.sample_id === activeAnnotationId
              ) ?? null)
            : null;
        if (!annotationLabelContext.annotationId && nextSelectedAnnotation) {
            setAnnotationId(nextSelectedAnnotation.sample_id);
        }

        editor = createSlicMaskEditor({
            segmentation: slicResult.segmentation,
            width: sample.width,
            height: sample.height,
            segmentationMask: nextSelectedAnnotation?.segmentation_details?.segmentation_mask
        });
        selectedAnnotation = nextSelectedAnnotation;
        clearPreview();
    });
    const onpointermove = (event: PointerEvent) => {
        const point = getImageCoordsFromMouse(
            event,
            interactionRect ?? null,
            sample.width,
            sample.height
        );
        if (isStrokeActive && point && editor) {
            const preview = stroke.extend(point);
            if (preview) renderStrokePreview(preview);
        } else {
            updateHover(point);
        }
    };
    const onpointerleave = () => {
        if (!isStrokeActive) clearPreview();
    };
    const onpointerdown = (event: PointerEvent) => {
        const point = getImageCoordsFromMouse(
            event,
            interactionRect ?? null,
            sample.width,
            sample.height
        );
        if (!point) return;
        const blocked =
            (event.button !== undefined && event.button !== 0) ||
            isPersisting ||
            !!(
                selectedAnnotation &&
                annotationLabelContext.isAnnotationLocked?.(selectedAnnotation.sample_id)
            );
        const selection = stroke.begin(point, blocked);
        if (!selection) {
            releasePointerCapture(event);
            return;
        }
        (event.currentTarget as Element | null)?.setPointerCapture?.(event.pointerId);
        setIsDrawing(true);
        renderStrokePreview(selection);
        updateHover(point);
    };
    const onpointercancel = (event: PointerEvent) => {
        releasePointerCapture(event);
        clearPreview();
        setIsDrawing(false);
    };
    return {
        get boundaryDataUrl() {
            return slic.boundaryDataUrl;
        },
        get strokeMaskDataUrl() {
            return preview.strokeMaskDataUrl;
        },
        get hoverMaskDataUrl() {
            return preview.hoverMaskDataUrl;
        },
        get labels() {
            return labels.data ?? [];
        },
        selectClassDialogOpen,
        handleSelectClassDialogConfirm,
        handleSelectClassDialogCancel,
        onpointermove,
        onpointerleave,
        onpointerdown,
        onpointerup: finishStroke,
        onpointercancel
    };
}
