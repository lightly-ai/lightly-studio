<script lang="ts">
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { getCreateLabelErrorMessage, useCreateLabel } from '$lib/hooks';
    import type { BoundingBox } from '$lib/types';
    import { drag, type D3DragEvent } from 'd3-drag';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';
    import { toast } from 'svelte-sonner';
    import { select } from 'd3-selection';
    import { onDestroy } from 'svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { useCollectionWithChildren } from '$lib/hooks/useCollection/useCollection';
    import { page } from '$app/state';
    import { addAnnotationCreateToUndoStack } from '$lib/services/addAnnotationCreateToUndoStack';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { usePendingOperations } from '$lib/hooks/usePendingOperations/usePendingOperations';
    import ResizableRectangle from '$lib/components/ResizableRectangle/ResizableRectangle.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
    import type { PendingChange } from '../pendingChange';
    import {
        isAnnotationSourceBlocked,
        usePendingBoxClass,
        usePostHog,
        useStickyClassName
    } from '$lib/hooks';
    import { createLabelIdLookup } from './createLabelIdLookup';
    import { usePendingBbox } from './usePendingBbox';

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
        hoverbbox?: boolean;
        onCreateBoundingBoxPendingChange?: (pendingChange: PendingChange) => void;
    };

    let {
        sample,
        interactionRect = $bindable<SVGRectElement>(),
        collectionId,
        refetch,
        sampleId,
        drawerStrokeColor,
        hoverbbox = $bindable(false),
        onCreateBoundingBoxPendingChange
    }: SampleObjectDetectionRectProps = $props();

    let temporaryBbox = $state<BoundingBox | null>(null);
    let shouldDisableInteraction = $state(false);
    let drawStartFired = false;
    const pendingBbox = usePendingBbox();
    const pendingBoxes = pendingBbox.boxes;
    const { trackEvent } = usePostHog();
    const labels = useAnnotationLabels(() => ({ collectionId }));

    const stickyClass = useStickyClassName(() => collectionId);
    const { requestClass, cancel: cancelPendingBoxClass } = usePendingBoxClass();

    const { createLabel } = useCreateLabel({ getCollectionId: () => collectionId });
    const { createAnnotation } = useCreateAnnotation({ getCollectionId: () => collectionId });
    const { deleteAnnotation } = useDeleteAnnotation({ getCollectionId: () => collectionId });
    const { addReversibleAction } = useGlobalStorage();

    const {
        startPending: startCreateBoundingBoxPending,
        endPending: endCreateBoundingBoxPending,
        resetPending: resetCreateBoundingBoxPending
    } = usePendingOperations({
        operationPrefix: 'bbox',
        onPendingChange: (pendingChange: PendingChange) => {
            onCreateBoundingBoxPendingChange?.(pendingChange);
        }
    });

    const cancelDrag = () => {
        setIsDrawing(false);
        temporaryBbox = null;
        drawStartFired = false;
    };

    const datasetId = $derived(page.params.dataset_id!);
    const { refetch: refetchRootCollection } = useCollectionWithChildren({
        getCollectionId: () => datasetId
    });

    const BOX_MIN_SIZE_PX = 4;
    const setupDragBehavior = () => {
        if (!interactionRect) return;

        const rectSelection = select(interactionRect);

        let startPoint: { x: number; y: number } | null = null;

        // Setup D3 drag behavior for annotation creation
        const dragBehavior = drag<SVGRectElement, unknown>()
            .on('start', (event: D3Event) => {
                // Remove focus from any selected annotation, and drop a box that waits for a class.
                setAnnotationId(null);
                cancelPendingBoxClass();
                setIsDrawing(true);
                if (!drawStartFired) {
                    trackEvent('annotation_draw_started', {
                        collection_id: collectionId,
                        tool: 'bounding-box',
                        parent_sample_type: page.params.collection_type
                    });
                    drawStartFired = true;
                }
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
                if (!temporaryBbox || !annotationLabelContext.isDrawing || !startPoint) return;

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
                if (!temporaryBbox || !annotationLabelContext.isDrawing) return;

                const drawn = temporaryBbox;
                // End the drag first: the card that asks for the class hides while drawing.
                cancelDrag();
                startPoint = null;

                // Only create annotation if the rectangle has meaningful size in both dimensions
                if (drawn.width > BOX_MIN_SIZE_PX && drawn.height > BOX_MIN_SIZE_PX) {
                    createObjectDetectionAnnotation(drawn, pendingBbox.start(drawn));
                }
            });

        rectSelection.call(dragBehavior);

        return () => {
            dragBehavior.on('start', null).on('drag', null).on('end', null);
        };
    };

    // `pendingToken` is the drawn box that stays on screen until the annotation is loaded.
    const createObjectDetectionAnnotation = async (bbox: BoundingBox, pendingToken: number) => {
        const className = await getNewBoxClass(bbox);
        if (!className) {
            pendingBbox.clear(pendingToken);
            return;
        }
        const pendingOperation = startCreateBoundingBoxPending();
        try {
            const newAnnotation = await createAnnotation({
                parent_sample_id: sampleId,
                annotation_type: 'object_detection',
                x: Math.round(bbox.x),
                y: Math.round(bbox.y),
                width: Math.round(bbox.width),
                height: Math.round(bbox.height),
                annotation_label_id: await getLabelId(className),
                annotation_collection_name: annotationLabelContext.annotationSource ?? undefined
            });
            onBoxCreated(newAnnotation, pendingToken);
            toast.success('Annotation created successfully');
        } catch (error) {
            pendingBbox.clear(pendingToken);
            toast.error(
                getCreateLabelErrorMessage(error, 'Failed to create annotation. Please try again.')
            );
            console.error('Error creating annotation:', error);
        } finally {
            endCreateBoundingBoxPending(pendingOperation);
        }
    };

    // The class for a new box, or null to drop the box. Without a sticky class the box waits for
    // a class picked at the box.
    const getNewBoxClass = async (bbox: BoundingBox): Promise<string | null> => {
        if (isAnnotationSourceBlocked(annotationLabelContext)) return null;
        return stickyClass.current ?? requestClass(bbox);
    };

    // The ID of the class with the name. A new name creates the class.
    const getLabelId = createLabelIdLookup({
        // Wait for the class list, so an existing class does not count as missing.
        getLabels: async () => labels.data ?? (await labels.refetch()).data ?? [],
        createLabel: async (className) => {
            const label = await createLabel({
                dataset_id: datasetId,
                annotation_label_name: className
            });
            return label.annotation_label_id!;
        }
    });

    const onBoxCreated = (newAnnotation: AnnotationView, pendingToken: number) => {
        if (sample.annotations.length == 0) refetchRootCollection();
        pendingBbox.created(pendingToken, newAnnotation.sample_id);
        addAnnotationCreateToUndoStack({
            annotation: newAnnotation,
            addReversibleAction,
            deleteAnnotation,
            refetch
        });
        refetch();
        // A box drawn since then keeps the focus: selecting this one would pull it away.
        if (!pendingBbox.isNewest(pendingToken) || annotationLabelContext.isDrawing) return;
        setLastCreatedAnnotationId(newAnnotation.sample_id);
        setAnnotationId(newAnnotation.sample_id);
        setCurrentBoundingBox(getBoundingBox(newAnnotation));
        // Enable resizing immediately after creation
        shouldDisableInteraction = true;
        hoverbbox = true;
    };
    const {
        context: annotationLabelContext,
        setLastCreatedAnnotationId,
        setAnnotationId,
        setIsDrawing,
        setCurrentBoundingBox
    } = useAnnotationLabelContext();

    const interactionPointerEvents = $derived(shouldDisableInteraction ? 'none' : 'all');

    const isPointInsideExistingAnnotation = (x: number, y: number) => {
        if (!annotationLabelContext.annotationId) return false;

        const bbox =
            annotationLabelContext.currentAnnotationBoundingBox ??
            (() => {
                const found = sample.annotations.find(
                    (annotation) => annotation.sample_id === annotationLabelContext.annotationId
                );
                return found ? getBoundingBox(found) : null;
            })();

        if (!bbox) return false;

        return x >= bbox.x && x <= bbox.x + bbox.width && y >= bbox.y && y <= bbox.y + bbox.height;
    };

    const updateInteractionLock = (clientX: number, clientY: number) => {
        if (!interactionRect || annotationLabelContext.isDrawing) {
            shouldDisableInteraction = false;
            hoverbbox = false;
            return;
        }

        const rect = interactionRect.getBoundingClientRect();
        const isOutside =
            clientX < rect.left ||
            clientX > rect.right ||
            clientY < rect.top ||
            clientY > rect.bottom;

        if (isOutside) {
            shouldDisableInteraction = false;
            hoverbbox = false;
            return;
        }

        const x = ((clientX - rect.left) / rect.width) * sample.width;
        const y = ((clientY - rect.top) / rect.height) * sample.height;

        const hovering = isPointInsideExistingAnnotation(x, y);

        shouldDisableInteraction = hovering;
        hoverbbox = hovering;
    };

    const handlePointerActivity = (event: PointerEvent) => {
        updateInteractionLock(event.clientX, event.clientY);
    };

    let detachSvgListeners: (() => void) | null = null;

    const attachSvgListeners = () => {
        // Listen on the parent SVG so hover updates even when the overlay sets pointer-events: none.
        const svg = interactionRect?.ownerSVGElement;
        if (!svg) return;

        svg.addEventListener('pointermove', handlePointerActivity, { passive: true });
        svg.addEventListener('pointerdown', handlePointerActivity, { passive: true });
        svg.addEventListener('pointerup', handlePointerActivity, { passive: true });

        return () => {
            svg.removeEventListener('pointermove', handlePointerActivity);
            svg.removeEventListener('pointerdown', handlePointerActivity);
            svg.removeEventListener('pointerup', handlePointerActivity);
        };
    };

    $effect(() => {
        detachSvgListeners?.();
        detachSvgListeners = attachSvgListeners() ?? null;
    });

    onDestroy(() => {
        resetCreateBoundingBoxPending();
        cancelPendingBoxClass();
        detachSvgListeners?.();
    });

    $effect(() => {
        pendingBbox.sync(sample.annotations.map((annotation) => annotation.sample_id));
    });

    // A pending box belongs to one sample; drop it when the view moves to another.
    $effect(() => {
        void sampleId;
        return () => {
            pendingBbox.clearAll();
            cancelPendingBoxClass();
        };
    });

    // Setup drag behavior when rect becomes available or mode changes
    $effect(() => {
        setupDragBehavior();
        shouldDisableInteraction = false;
        hoverbbox = false;
    });
</script>

{#if temporaryBbox && annotationLabelContext.isDrawing}
    <ResizableRectangle
        bbox={temporaryBbox}
        colorStroke={drawerStrokeColor}
        colorFill="rgba(0, 123, 255, 0.1)"
        opacity={0.8}
        scale={1}
    />
{/if}
{#each $pendingBoxes as pending (pending.token)}
    <ResizableRectangle
        bbox={pending.bbox}
        colorStroke={drawerStrokeColor}
        colorFill="rgba(0, 123, 255, 0.1)"
        opacity={0.8}
        scale={1}
    />
{/each}
<SampleAnnotationRect
    bind:interactionRect
    cursor={'crosshair'}
    pointerEvents={interactionPointerEvents}
    {sample}
/>
