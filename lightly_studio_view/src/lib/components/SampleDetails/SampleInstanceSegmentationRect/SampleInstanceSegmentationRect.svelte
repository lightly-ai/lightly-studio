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
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
    import type { BoundingBox } from '$lib/types';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';
    import { toast } from 'svelte-sonner';

    type SampleInstanceSegmentationRectProps = {
        sample: {
            width: number;
            height: number;
            annotations: AnnotationView[];
        };
        interactionRect?: SVGRectElement | undefined | null;
        segmentationPath: { x: number; y: number }[];
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
        refetch
    }: SampleInstanceSegmentationRectProps = $props();

    const labels = useAnnotationLabels({ collectionId });
    const { createLabel } = useCreateLabel({ collectionId });
    const { createAnnotation } = useCreateAnnotation({
        collectionId
    });

    const annotationApi = $derived.by(() => {
        if (!annotationLabelContext.annotationId) return null;

        return useAnnotation({
            collectionId,
            annotationId: annotationLabelContext.annotationId!
        });
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

    const finishBrush = async () => {
        if (!annotationLabelContext.isDrawing || !workingMask) {
            reset();
            return;
        }

        annotationLabelContext.isDrawing = false;

        const bbox = computeBoundingBoxFromMask(workingMask, sample.width, sample.height);

        if (!bbox) {
            toast.error('Invalid segmentation mask');
            reset();
            return;
        }

        const rle = encodeBinaryMaskToRLE(workingMask);

        if (selectedAnnotation) {
            await onUpdateSegmentationMask(bbox, rle);
        } else {
            let label =
                $labels.data?.find(
                    (label) =>
                        label.annotation_label_name === annotationLabelContext.annotationLabel
                ) ?? $labels.data?.find((label) => label.annotation_label_name === 'default');

            // Create an default label if it does not exist yet
            if (!label) {
                label = await createLabel({
                    dataset_id: collectionId,
                    annotation_label_name: 'default'
                });
            }

            const newAnnotation = await createAnnotation({
                parent_sample_id: sampleId,
                annotation_type: 'instance_segmentation',
                x: bbox.x,
                y: bbox.y,
                width: bbox.width,
                height: bbox.height,
                segmentation_mask: rle,
                annotation_label_id: label.annotation_label_id!
            });

            annotationLabelContext.annotationLabel = label.annotation_label_name;
            annotationLabelContext.annotationId = newAnnotation.sample_id;
        }

        refetch();
        reset();
    };

    const reset = () => {
        brushPath = [];
        workingMask = null;
        previewRLE = [];
        annotationLabelContext.isDrawing = false;
    };

    const onUpdateSegmentationMask = (bbox: BoundingBox, rle: number[]) => {
        try {
            return annotationApi?.updateAnnotation({
                annotation_id: annotationLabelContext.annotationId!,
                collection_id: collectionId,
                bounding_box: bbox,
                segmentation_mask: rle
            });
        } catch (error) {
            console.error('Failed to update annotation:', (error as Error).message);
        }
    };
</script>

{#if brushPath.length > 0}
    <circle
        cx={brushPath.at(-1)!.x}
        cy={brushPath.at(-1)!.y}
        r={brushRadius}
        fill={withAlpha(drawerStrokeColor, 0.2)}
        stroke={drawerStrokeColor}
    />
{/if}
{#if previewRLE.length > 0}
    <SampleAnnotationSegmentationRLE
        segmentation={previewRLE}
        width={sample.width}
        colorFill={withAlpha(drawerStrokeColor, 0.65)}
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
    onpointerleave={finishBrush}
    onpointerup={finishBrush}
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
