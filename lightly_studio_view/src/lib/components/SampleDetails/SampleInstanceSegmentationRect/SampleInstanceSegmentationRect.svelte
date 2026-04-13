<script lang="ts">
    import { onDestroy } from 'svelte';
    import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
    import {
        decodeRLEToBinaryMask,
        getImageCoordsFromMouse,
        withAlpha
    } from '$lib/components/SampleAnnotation/utils';
    import parseColor from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useInstanceSegmentationBrush } from '$lib/hooks/useInstanceSegmentationBrush';
    import { useInstanceSegmentationPreview } from '$lib/hooks/useInstanceSegmentationPreview';
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
        annotationType?: string | null | undefined;
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
    const activeAnnotationId = $derived.by(() => {
        if (annotationLabelContext.annotationId) return annotationLabelContext.annotationId;

        if (annotationLabelContext.isOnAnnotationDetailsView) {
            return sample.annotations[0]?.sample_id ?? null;
        }

        return null;
    });
    const annotationApi = $derived.by(() => {
        if (!activeAnnotationId) return null;

        return useAnnotation({
            collectionId,
            annotationId: activeAnnotationId
        });
    });
    const datasetId = $derived(page.params.dataset_id!);
    const { refetch: refetchRootCollection } = $derived.by(() =>
        useCollectionWithChildren({ collectionId: datasetId })
    );
    const brushApi = $derived.by(() =>
        useInstanceSegmentationBrush({
            collectionId,
            datasetId,
            sampleId,
            sample,
            annotations: sample.annotations,
            refetch,
            onAnnotationCreated: () => {
                // Only refresh root collection if there were no annotations before
                if (sample.annotations.length === 0) {
                    refetchRootCollection();
                }
            }
        })
    );

    const {
        context: annotationLabelContext,
        setIsDrawing,
        setAnnotationId
    } = useAnnotationLabelContext();

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

    onDestroy(() => {
        previewApi.destroy();
    });

    $effect(() => {
        if (!activeAnnotationId) {
            previewApi.cancelScheduledPreviewCompose();
            previewApi.clearPreview();
            isPreviewVisible = false;
            selectedAnnotation = null;
            baseMask = null;
            lastBrushPoint = null;
            return;
        }

        if (!annotationLabelContext.annotationId && activeAnnotationId) {
            setAnnotationId(activeAnnotationId);
        }

        const ann = sample.annotations?.find((a) => a.sample_id === activeAnnotationId);

        const rle = ann?.segmentation_details?.segmentation_mask;
        if (!ann) {
            previewApi.cancelScheduledPreviewCompose();
            previewApi.clearPreview();
            isPreviewVisible = false;
            const emptyMask = new Uint8Array(sample.width * sample.height);
            baseMask = emptyMask;
            selectedAnnotation = null;
            lastBrushPoint = null;
            return;
        }

        if (!rle) {
            previewApi.cancelScheduledPreviewCompose();
            previewApi.clearPreview();
            isPreviewVisible = false;
            const emptyMask = new Uint8Array(sample.width * sample.height);
            baseMask = emptyMask;
            selectedAnnotation = ann;
            lastBrushPoint = null;
            return;
        }

        previewApi.cancelScheduledPreviewCompose();
        const decodedMask = decodeRLEToBinaryMask(rle, sample.width, sample.height);
        // Base mask is copied into the source canvas on pointer down.
        baseMask = decodedMask;
        selectedAnnotation = ann;
        previewApi.clearPreview();
        isPreviewVisible = false;
        lastBrushPoint = null;
    });

    const updateAnnotation = async (input: AnnotationUpdateInput) => {
        await annotationApi?.updateAnnotation(input);
        refetch();
    };

    const resolveSelectedAnnotation = () => {
        if (selectedAnnotation) return selectedAnnotation;
        if (!activeAnnotationId) return null;

        return sample.annotations.find((a) => a.sample_id === activeAnnotationId) ?? null;
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
    cursor={'crosshair'}
    onpointermove={(e) => {
        if (!annotationLabelContext.isDrawing) return;
        const currentAnnotation = resolveSelectedAnnotation();
        if (
            currentAnnotation &&
            annotationLabelContext.isAnnotationLocked?.(currentAnnotation.sample_id)
        )
            return;

        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);
        if (!point) return;

        if (lastBrushPoint) {
            // Connect sampled points; dot-only strokes leave gaps on fast movement.
            previewApi.drawBrushLine({
                from: lastBrushPoint,
                to: point,
                brushRadius,
                width: sample.width,
                height: sample.height
            });
            previewApi.drawBrushDot({
                point,
                brushRadius,
                width: sample.width,
                height: sample.height
            });
        } else {
            previewApi.drawBrushDot({
                point,
                brushRadius,
                width: sample.width,
                height: sample.height
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
    onpointerup={(e) => {
        lastBrushPoint = null;
        e.currentTarget?.releasePointerCapture?.(e.pointerId);
        previewApi.cancelScheduledPreviewCompose();
        previewApi.clearPreview();
        isPreviewVisible = false;

        const targetAnnotation = resolveSelectedAnnotation();
        if (
            targetAnnotation &&
            annotationLabelContext.isAnnotationLocked?.(targetAnnotation.sample_id)
        ) {
            return;
        }

        const updatedMask = previewApi.toBinaryMaskFromSourceCanvas(sample.width, sample.height);
        if (!updatedMask) return;
        // Keep local base in sync after committing stroke.
        baseMask = updatedMask;

        brushApi.finishBrush(
            updatedMask,
            targetAnnotation,
            $labels.data ?? [],
            updateAnnotation,
            annotationLabelContext.lockedAnnotationIds
        );
    }}
    onpointerdown={(e) => {
        e.currentTarget?.setPointerCapture?.(e.pointerId);

        const point = getImageCoordsFromMouse(e, interactionRect, sample.width, sample.height);
        if (!point) return;

        if (!annotationLabelContext.annotationId && activeAnnotationId) {
            setAnnotationId(activeAnnotationId);
        }

        const targetAnnotation = resolveSelectedAnnotation();
        if (
            targetAnnotation &&
            annotationLabelContext.isAnnotationLocked?.(targetAnnotation.sample_id)
        ) {
            e.currentTarget?.releasePointerCapture?.(e.pointerId);
            return;
        }

        setIsDrawing(true);
        lastBrushPoint = point;
        isPreviewVisible = false;
        previewApi.cancelScheduledPreviewCompose();
        previewApi.drawMaskToSourceCanvas(baseMask, sample.width, sample.height);
        previewApi.drawBrushDot({
            point,
            brushRadius,
            width: sample.width,
            height: sample.height
        });
        previewApi.schedulePreviewCompose({
            width: sample.width,
            height: sample.height,
            color: parsedColor,
            isDrawing: Boolean(annotationLabelContext.isDrawing)
        });
    }}
/>

<style>
    .previewHidden {
        visibility: hidden;
    }
</style>
