<script lang="ts">
    import {
        computeBoundingBoxFromMask,
        encodeBinaryMaskToRLE,
        getImageCoordsFromMouse,
        withAlpha
    } from '$lib/components/SampleAnnotation/utils';
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
        draftAnnotationLabel?: string | null | undefined;
        refetch: () => void;
    };

    let {
        sample,
        interactionRect = $bindable<SVGRectElement>(),
        segmentationPath,
        sampleId,
        collectionId,
        draftAnnotationLabel,
        brushRadius,
        drawerStrokeColor,
        refetch
    }: SampleInstanceSegmentationRectProps = $props();

    let isDrawingSegmentation = $state(false);

    const labels = useAnnotationLabels({ collectionId });
    const { createLabel } = useCreateLabel({ collectionId });
    const { createAnnotation } = useCreateAnnotation({
        collectionId
    });

    const handleSegmentationClick = (event: MouseEvent) => {
        if (!isDrawingSegmentation) {
            const point = getImageCoordsFromMouse(
                event,
                interactionRect,
                sample.width,
                sample.height
            );
            if (!point) return;

            isDrawingSegmentation = true;
            segmentationPath = [point];
        } else {
            finishSegmentationDraw();
        }
    };

    // Append the mouse point to the segmentation path while drawing.
    const continueSegmentationDraw = (event: MouseEvent) => {
        if (!isDrawingSegmentation) return;

        const point = getImageCoordsFromMouse(event, interactionRect, sample.width, sample.height);

        if (!point) return;

        segmentationPath = [...segmentationPath, point];
    };

    const finishSegmentationDraw = async () => {
        if (!isDrawingSegmentation || segmentationPath.length < 3) {
            isDrawingSegmentation = false;
            segmentationPath = [];
            return;
        }

        isDrawingSegmentation = false;

        // Close polygon
        const closedPath = [...segmentationPath, segmentationPath[0]];

        await createSegmentationRLE(closedPath);

        segmentationPath = [];
    };

    const createSegmentationRLE = async (polygon: { x: number; y: number }[]) => {
        if (!draftAnnotationLabel || !$labels.data) return;

        let label = $labels.data.find((l) => l.annotation_label_name === draftAnnotationLabel);

        if (!label) {
            label = await createLabel({
                dataset_id: collectionId,
                annotation_label_name: draftAnnotationLabel
            });
        }

        const imageWidth = sample.width;
        const imageHeight = sample.height;

        const mask = rasterizePolygonToMask(polygon, imageWidth, imageHeight);

        const bbox = computeBoundingBoxFromMask(mask, imageWidth, imageHeight);

        if (!bbox) {
            toast.error('Invalid segmentation mask');
            return;
        }

        const rle = encodeBinaryMaskToRLE(mask);

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
    };

    const rasterizePolygonToMask = (
        polygon: { x: number; y: number }[],
        width: number,
        height: number
    ): Uint8Array => {
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d')!;
        ctx.clearRect(0, 0, width, height);

        ctx.beginPath();
        polygon.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
        ctx.closePath();
        ctx.fillStyle = 'white';
        ctx.fill();

        const imageData = ctx.getImageData(0, 0, width, height).data;

        // Binary mask: 1 = foreground, 0 = background
        const mask = new Uint8Array(width * height);

        for (let i = 0; i < width * height; i++) {
            mask[i] = imageData[i * 4 + 3] > 0 ? 1 : 0; // alpha channel
        }

        return mask;
    };
</script>

{#if segmentationPath.length > 1 && draftAnnotationLabel}
    <path
        d={`M ${segmentationPath.map((p) => `${p.x},${p.y}`).join(' L ')}`}
        fill={withAlpha(drawerStrokeColor, 0.08)}
        stroke={drawerStrokeColor}
        stroke-width={brushRadius}
        vector-effect="non-scaling-stroke"
    />
{/if}
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor={'crosshair'}
    onclick={handleSegmentationClick}
    onpointermove={continueSegmentationDraw}
    onpointerleave={() => finishSegmentationDraw()}
/>
