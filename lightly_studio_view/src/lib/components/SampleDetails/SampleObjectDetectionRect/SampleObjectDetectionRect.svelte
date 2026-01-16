<script lang="ts">
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
    import type { BoundingBox } from '$lib/types';
    import { drag, type D3DragEvent } from 'd3-drag';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';
    import { toast } from 'svelte-sonner';
    import { select } from 'd3-selection';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { useRootCollectionOptions } from '$lib/hooks/useRootCollection/useRootCollection';
    import { addAnnotationCreateToUndoStack } from '$lib/services/addAnnotationCreateToUndoStack';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import ResizableRectangle from '$lib/components/ResizableRectangle/ResizableRectangle.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';

    type D3Event = D3DragEvent<SVGRectElement, unknown, unknown>;

    type SampleObjectDetectionRectProps = {
        sample: {
            width: number;
            height: number;
            annotations: AnnotationView[];
        };
        interactionRect?: SVGRectElement | undefined | null;
        sampleId: string;
        collectionId: string;
        drawerStrokeColor: string;
        refetch: () => void;
    };

    let {
        sample,
        interactionRect = $bindable<SVGRectElement>(),
        collectionId,
        refetch,
        sampleId,
        drawerStrokeColor
    }: SampleObjectDetectionRectProps = $props();

    let temporaryBbox = $state<BoundingBox | null>(null);
    const labels = useAnnotationLabels({ collectionId });
    const { createLabel } = useCreateLabel({ collectionId });
    const { createAnnotation } = useCreateAnnotation({
        collectionId
    });
    const { deleteAnnotation } = useDeleteAnnotation({
        collectionId
    });
    const { addReversibleAction } = useGlobalStorage();

    const cancelDrag = () => {
        annotationLabelContext.isDragging = false;
        temporaryBbox = null;
    };

    const { refetch: refetchRootCollection } = useRootCollectionOptions({
        collectionId
    });

    const BOX_MIN_SIZE_PX = 4;
    const setupDragBehavior = () => {
        if (!interactionRect) return;

        const rectSelection = select(interactionRect);

        let startPoint: { x: number; y: number } | null = null;

        // Setup D3 drag behavior for annotation creation
        const dragBehavior = drag<SVGRectElement, unknown>()
            .on('start', (event: D3Event) => {
                // Remove focus from any selected annotation.
                annotationLabelContext.annotationId = null;
                annotationLabelContext.isDragging = true;
                // Get mouse position relative to the SVG element
                const svgRect = interactionRect!.getBoundingClientRect();
                const clientX = event.sourceEvent.clientX;
                const clientY = event.sourceEvent.clientY;
                const x = ((clientX - svgRect.left) / svgRect.width) * sample.width;
                const y = ((clientY - svgRect.top) / svgRect.height) * sample.height;

                startPoint = { x, y };
                temporaryBbox = { x, y, width: 0, height: 0 };
            })
            .on('drag', (event: D3Event) => {
                if (!temporaryBbox || !annotationLabelContext.isDragging || !startPoint) return;

                // Get current mouse position relative to the SVG element
                const svgRect = interactionRect!.getBoundingClientRect();
                const clientX = event.sourceEvent.clientX;
                const clientY = event.sourceEvent.clientY;
                let currentX = ((clientX - svgRect.left) / svgRect.width) * sample.width;
                let currentY = ((clientY - svgRect.top) / svgRect.height) * sample.height;

                // Constrain current position to image bounds
                const imageWidth = sample.width;
                const imageHeight = sample.height;
                currentX = Math.max(0, Math.min(currentX, imageWidth));
                currentY = Math.max(0, Math.min(currentY, imageHeight));

                const x = Math.min(startPoint.x, currentX);
                const y = Math.min(startPoint.y, currentY);
                const width = Math.abs(currentX - startPoint.x);
                const height = Math.abs(currentY - startPoint.y);

                temporaryBbox = { x, y, width, height };
            })
            .on('end', () => {
                if (!temporaryBbox || !annotationLabelContext.isDragging) return;

                // Only create annotation if the rectangle has meaningful size (> 10px in both dimensions)
                if (
                    temporaryBbox.width > BOX_MIN_SIZE_PX &&
                    temporaryBbox.height > BOX_MIN_SIZE_PX
                ) {
                    createObjectDetectionAnnotation({
                        x: temporaryBbox.x,
                        y: temporaryBbox.y,
                        width: temporaryBbox.width,
                        height: temporaryBbox.height
                    });
                }

                cancelDrag();
                startPoint = null;
            });

        rectSelection.call(dragBehavior);

        return () => {
            dragBehavior.on('start', null).on('drag', null).on('end', null);
        };
    };

    const createObjectDetectionAnnotation = async ({
        x,
        y,
        width,
        height
    }: {
        x: number;
        y: number;
        width: number;
        height: number;
    }) => {
        let label =
            $labels.data?.find(
                (label) => label.annotation_label_name === annotationLabelContext.annotationLabel
            ) ?? $labels.data?.find((label) => label.annotation_label_name === 'DEFAULT');

        // Create an default label if it does not exist yet
        if (!label) {
            label = await createLabel({
                dataset_id: collectionId,
                annotation_label_name: 'DEFAULT'
            });
        }

        try {
            const newAnnotation = await createAnnotation({
                parent_sample_id: sampleId,
                annotation_type: 'object_detection',
                x: Math.round(x),
                y: Math.round(y),
                width: Math.round(width),
                height: Math.round(height),
                annotation_label_id: label.annotation_label_id!
            });

            if (sample.annotations.length == 0) {
                refetchRootCollection();
            }

            addAnnotationCreateToUndoStack({
                annotation: newAnnotation,
                addReversibleAction,
                deleteAnnotation,
                refetch
            });

            refetch();

            setLastCreatedAnnotationId(newAnnotation.sample_id);
            setAnnotationId(newAnnotation.sample_id);

            toast.success('Annotation created successfully');
            return newAnnotation;
        } catch (error) {
            toast.error('Failed to create annotation. Please try again.');
            console.error('Error creating annotation:', error);
            return;
        }
    };
    const {
        context: annotationLabelContext,
        setLastCreatedAnnotationId,
        setAnnotationId
    } = useAnnotationLabelContext();

    // Setup drag behavior when rect becomes available or mode changes
    $effect(() => {
        setupDragBehavior();
    });
</script>

{#if temporaryBbox && annotationLabelContext.isDragging}
    <ResizableRectangle
        bbox={temporaryBbox}
        colorStroke={drawerStrokeColor}
        colorFill="rgba(0, 123, 255, 0.1)"
        opacity={0.8}
        scale={1}
    />
{/if}
<SampleAnnotationRect bind:interactionRect cursor={'crosshair'} {sample} />
