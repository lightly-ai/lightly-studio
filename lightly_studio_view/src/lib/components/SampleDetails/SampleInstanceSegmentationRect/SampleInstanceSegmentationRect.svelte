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
        annotationType: annotationTypeProp = 'instance_segmentation',
        refetch
    }: SampleInstanceSegmentationRectProps = $props();
    const resolvedAnnotationType = $derived(annotationTypeProp);

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
            sampleId,
            sample,
            annotations: sample.annotations,
            segmentationMode:
                resolvedAnnotationType === 'semantic_segmentation' ? 'semantic' : 'instance',
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

    let brushPath = $state<{ x: number; y: number }[]>([]);
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
        if (!activeAnnotationId) {
            selectedAnnotation = null;
            workingMask = null;
            brushPath = [];
            previewDataUrl = '';
            return;
        }

        if (!annotationLabelContext.annotationId && activeAnnotationId) {
            setAnnotationId(activeAnnotationId);
        }

        const ann = sample.annotations?.find((a) => a.sample_id === activeAnnotationId);

        const rle = ann?.segmentation_details?.segmentation_mask;
        if (!ann) {
            workingMask = new Uint8Array(sample.width * sample.height);
            previewDataUrl = '';
            selectedAnnotation = null;
            return;
        }

        if (!rle) {
            workingMask = new Uint8Array(sample.width * sample.height);
            previewDataUrl = '';
            selectedAnnotation = ann;
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

    const resolveSelectedAnnotation = () => {
        if (selectedAnnotation) return selectedAnnotation;
        if (!activeAnnotationId) return null;

        return sample.annotations.find((a) => a.sample_id === activeAnnotationId) ?? null;
    };

    const isLocked = (annotationId: string | null | undefined) =>
        annotationLabelContext.lockedAnnotationIds?.has(annotationId ?? '') ?? false;
</script>

{#if mousePosition}
    <circle
        cx={mousePosition.x}
        cy={mousePosition.y}
        r={brushRadius}
        fill={withAlpha(drawerStrokeColor, 0.25)}
    />
{/if}
{#if previewDataUrl && annotationLabelContext.isDrawing}
    <image href={previewDataUrl} width={sample.width} height={sample.height} opacity={0.85} />
{/if}
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor={'crosshair'}
    onpointermove={(e) => {
        if (!annotationLabelContext.isDrawing || !workingMask) return;
        const currentAnnotation = resolveSelectedAnnotation();
        if (currentAnnotation && isLocked(currentAnnotation.sample_id)) return;

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
        updatePreview();
    }}
    onpointerup={(e) => {
        lastBrushPoint = null;
        e.currentTarget?.releasePointerCapture?.(e.pointerId);

        const targetAnnotation = resolveSelectedAnnotation();
        if (targetAnnotation && isLocked(targetAnnotation.sample_id)) {
            return;
        }

        brushApi.finishBrush(
            workingMask,
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
        if (targetAnnotation && isLocked(targetAnnotation.sample_id)) {
            e.currentTarget?.releasePointerCapture?.(e.pointerId);
            return;
        }

        setIsDrawing(true);
        lastBrushPoint = point;
        brushPath = [point];

        if (!workingMask) {
            workingMask = new Uint8Array(sample.width * sample.height);
        }

        applyBrushToMask(workingMask, sample.width, sample.height, [point], brushRadius, 1);
        updatePreview();
    }}
/>
