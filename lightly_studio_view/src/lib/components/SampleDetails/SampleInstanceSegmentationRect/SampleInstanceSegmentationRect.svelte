<script lang="ts">
    import { SampleAnnotationSegmentationRLE } from '$lib/components';
    import {
        applyBrushToMask,
        computeBoundingBoxFromMask,
        encodeBinaryMaskToRLE,
        getImageCoordsFromMouse,
        withAlpha
    } from '$lib/components/SampleAnnotation/utils';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';
    import { toast } from 'svelte-sonner';

    type SampleInstanceSegmentationRectProps = {
        sample: {
            width: number;
            height: number;
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
    const annotationLabelContext = useAnnotationLabelContext();

    let brushPath = $state<{ x: number; y: number }[]>([]);
    let workingMask = $state<Uint8Array | null>(null);
    let previewRLE = $state<number[] | null>(null);

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

        let label =
            $labels.data?.find(
                (label) => label.annotation_label_name === annotationLabelContext.annotationLabel
            ) ?? $labels.data?.find((label) => label.annotation_label_name === 'default');

        // Create an default label if it does not exist yet
        if (!label) {
            label = await createLabel({
                dataset_id: collectionId,
                annotation_label_name: 'default'
            });
        }

        const bbox = computeBoundingBoxFromMask(workingMask, sample.width, sample.height);

        if (!bbox) {
            toast.error('Invalid segmentation mask');
            reset();
            return;
        }

        const rle = encodeBinaryMaskToRLE(workingMask);

        await createAnnotation({
            parent_sample_id: sampleId,
            annotation_type: 'instance_segmentation',
            x: bbox.x,
            y: bbox.y,
            width: bbox.width,
            height: bbox.height,
            segmentation_mask: rle,
            annotation_label_id: label.annotation_label_id!
        });

        refetch();
        reset();
    };

    const reset = () => {
        brushPath = [];
        workingMask = null;
        previewRLE = null;
        annotationLabelContext.isDrawing = false;
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
{#if previewRLE}
    <SampleAnnotationSegmentationRLE
        segmentation={previewRLE}
        width={sample.width}
        colorFill={withAlpha(drawerStrokeColor, 0.2)}
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
        brushPath = [point];

        if (!workingMask) {
            workingMask = new Uint8Array(sample.width * sample.height);
        }

        applyBrushToMask(workingMask, sample.width, sample.height, [point], brushRadius, 1);
        updatePreview();
    }}
/>
