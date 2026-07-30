<script lang="ts">
    import { onDestroy } from 'svelte';
    import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
    import {
        decodeRLEToBinaryMask,
        getImageCoordsFromMouse,
        maskToDataUrl
    } from '$lib/components/SampleAnnotation/utils';
    import parseColor from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor';
    import SelectClassDialog from '$lib/components/SelectClassDialog/SelectClassDialog.svelte';
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
    import { loadSuperpixelsForImage, type SlicResult } from '$lib/utils/slic';
    import {
        createSuperpixelMaskEditor,
        type SuperpixelMaskEditor,
        type SuperpixelStrokePreview
    } from '@lightly-ai/slic';
    import { page } from '$app/state';
    import type { PendingChange } from '../pendingChange';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';

    type SampleSlicRectProps = {
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
    };

    let {
        sample,
        interactionRect = $bindable<SVGRectElement>(),
        sampleId,
        collectionId,
        drawerStrokeColor,
        imageUrl,
        refetch,
        onFinishBrushPendingChange
    }: SampleSlicRectProps = $props();

    const labels = useAnnotationLabels(() => ({ collectionId }));
    const { deleteAnnotation } = useDeleteAnnotation({ collectionId });
    const {
        open: selectClassDialogOpen,
        requestLabel,
        handleConfirm: handleSelectClassDialogConfirm,
        handleCancel: handleSelectClassDialogCancel
    } = useSelectClassDialog();
    const datasetId = $derived(page.params.dataset_id!);
    const { refetch: refetchRootCollection } = $derived.by(() =>
        useCollectionWithChildren({ collectionId: datasetId })
    );
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

    let slicResult = $state<SlicResult | null>(null);
    let selectedAnnotation = $state<AnnotationView | null>(null);
    let boundaryDataUrl = $state('');
    let hoverMaskDataUrl = $state('');
    let strokeMaskDataUrl = $state('');
    let isStrokeActive = $state(false);
    let isPersisting = $state(false);
    let loadKey = $state<string | null>(null);
    let editor: SuperpixelMaskEditor | null = null;
    let hoveredLabel: number | null = null;

    const parsedColor = $derived(parseColor(drawerStrokeColor));
    const boundaryColor = $derived({ ...parsedColor, a: 170 });
    const previewColor = $derived({ ...parsedColor, a: 85 });

    const clearPreview = () => {
        hoveredLabel = null;
        hoverMaskDataUrl = '';
        strokeMaskDataUrl = '';
        isStrokeActive = false;
    };

    const renderStrokePreview = (preview: SuperpixelStrokePreview) => {
        if (!slicResult) return;
        strokeMaskDataUrl = maskToDataUrl(
            preview.mask,
            slicResult.segmentation.width,
            slicResult.segmentation.height,
            previewColor
        );
    };

    const updateHover = (point: { x: number; y: number } | null) => {
        if (!point || !editor || !slicResult) return;
        const label = editor.getLabelAtPoint(point);
        if (label === hoveredLabel) return;

        hoveredLabel = label;
        hoverMaskDataUrl = maskToDataUrl(
            editor.getSegmentPreviewMask(label),
            slicResult.segmentation.width,
            slicResult.segmentation.height,
            previewColor
        );
    };

    const loadSlicResult = async (key: string) => {
        setSlicStatus('computing');
        clearPreview();
        editor = null;
        try {
            const result = await loadSuperpixelsForImage({
                imageUrl,
                level: toolbarContext.slic.level
            });
            if (loadKey !== key) return;
            slicResult = result;
            setSlicStatus('ready');
        } catch (error) {
            if (loadKey !== key) return;
            console.error('Failed to compute SLIC superpixels:', error);
            slicResult = null;
            boundaryDataUrl = '';
            setSlicStatus('error');
        }
    };

    const releasePointerCapture = (event: PointerEvent) => {
        const target = event.currentTarget as Element | null;
        target?.releasePointerCapture?.(event.pointerId);
    };

    const finishStroke = (event: PointerEvent) => {
        releasePointerCapture(event);
        if (!isStrokeActive || !editor) return;

        isStrokeActive = false;
        strokeMaskDataUrl = '';
        const mask = editor.commitStroke();
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
            } catch (error) {
                console.error('Failed to finish SLIC stroke:', error);
            } finally {
                isPersisting = false;
                endFinishBrushPending(pendingOperation);
            }
        })();
    };

    onDestroy(() => {
        resetFinishBrushPending();
        setIsDrawing(false);
    });

    $effect(() => {
        const nextKey =
            toolbarContext.status === 'slic'
                ? `${imageUrl}::${toolbarContext.slic.level}::${toolbarContext.slic.retryCount}`
                : null;
        if (nextKey === loadKey) return;

        loadKey = nextKey;
        slicResult = null;
        boundaryDataUrl = '';
        clearPreview();
        editor = null;
        if (nextKey) void loadSlicResult(nextKey);
    });

    $effect(() => {
        if (!slicResult) return;
        boundaryDataUrl = maskToDataUrl(
            slicResult.segmentation.boundaries,
            slicResult.segmentation.width,
            slicResult.segmentation.height,
            boundaryColor
        );
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

        const rle = nextSelectedAnnotation?.segmentation_details?.segmentation_mask;
        const mask = rle
            ? decodeRLEToBinaryMask(rle, sample.width, sample.height)
            : new Uint8Array(sample.width * sample.height);
        editor = createSuperpixelMaskEditor({
            segmentation: slicResult.segmentation,
            mask,
            targetWidth: sample.width,
            targetHeight: sample.height,
            scaleX: slicResult.scaleX,
            scaleY: slicResult.scaleY
        });
        selectedAnnotation = nextSelectedAnnotation;
        clearPreview();
    });
</script>

{#if slicResult && boundaryDataUrl}
    <image href={boundaryDataUrl} width={sample.width} height={sample.height} opacity={0.9} />
{/if}
{#if slicResult && strokeMaskDataUrl}
    <image href={strokeMaskDataUrl} width={sample.width} height={sample.height} />
{/if}
{#if slicResult && hoverMaskDataUrl}
    <image href={hoverMaskDataUrl} width={sample.width} height={sample.height} />
{/if}
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor="crosshair"
    onpointermove={(event) => {
        const point = getImageCoordsFromMouse(event, interactionRect, sample.width, sample.height);
        if (isStrokeActive && point && editor) {
            const preview = editor.extendStroke(point);
            if (preview) renderStrokePreview(preview);
        } else {
            updateHover(point);
        }
    }}
    onpointerleave={() => {
        if (!isStrokeActive) clearPreview();
    }}
    onpointerdown={(event) => {
        if (
            !editor ||
            isPersisting ||
            (selectedAnnotation &&
                annotationLabelContext.isAnnotationLocked?.(selectedAnnotation.sample_id))
        ) {
            releasePointerCapture(event);
            return;
        }

        const point = getImageCoordsFromMouse(event, interactionRect, sample.width, sample.height);
        if (!point) return;
        event.currentTarget?.setPointerCapture?.(event.pointerId);
        setIsDrawing(true);
        isStrokeActive = true;
        renderStrokePreview(editor.beginStroke(point));
        updateHover(point);
    }}
    onpointerup={finishStroke}
    onpointercancel={(event) => {
        releasePointerCapture(event);
        editor?.cancelStroke();
        clearPreview();
        setIsDrawing(false);
    }}
/>

<SelectClassDialog
    bind:open={$selectClassDialogOpen}
    labels={labels.data?.map((label) => label.annotation_label_name ?? '').filter(Boolean) ?? []}
    onConfirm={handleSelectClassDialogConfirm}
    onCancel={handleSelectClassDialogCancel}
/>
