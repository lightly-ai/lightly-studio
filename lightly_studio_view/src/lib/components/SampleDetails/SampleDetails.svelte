<script lang="ts">
    import { afterNavigate, goto } from '$app/navigation';
    import { Card, CardContent, SampleDetailsSidePanel, SelectableBox } from '$lib/components';
    import { ImageAdjustments } from '$lib/components/ImageAdjustments';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import SampleDetailsBreadcrumb from './SampleDetailsBreadcrumb/SampleDetailsBreadcrumb.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useSettings } from '$lib/hooks/useSettings';
    import { routeHelpers } from '$lib/routes';
    import { type Snippet } from 'svelte';
    import { toast } from 'svelte-sonner';
    import type { QueryObserverResult } from '@tanstack/svelte-query';
    import _ from 'lodash';

    import { get } from 'svelte/store';
    import { ZoomableContainer } from '$lib/components';
    import { getImageURL } from '$lib/utils/getImageURL';
    import { useImage } from '$lib/hooks/useImage/useImage';
    import type { Collection } from '$lib/services/types';
    import { getAnnotations } from '../SampleAnnotation/utils';
    import Spinner from '../Spinner/Spinner.svelte';
    import {
        AnnotationType,
        type AnnotationView,
        type ImageView
    } from '$lib/api/lightly_studio_local';
    import type { BoundingBox } from '$lib/types';
    import SampleDetailsAnnotation from './SampleDetailsAnnotation/SampleDetailsAnnotation.svelte';
    import ResizableRectangle from '../ResizableRectangle/ResizableRectangle.svelte';
    import { drag, type D3DragEvent } from 'd3-drag';
    import { select } from 'd3-selection';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
    import type { ListItem } from '../SelectList/types';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { getColorByLabel } from '$lib/utils';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { useDeleteCaption } from '$lib/hooks/useDeleteCaption/useDeleteCaption';
    import { addAnnotationCreateToUndoStack } from '$lib/services/addAnnotationCreateToUndoStack';
    import { addAnnotationDeleteToUndoStack } from '$lib/services/addAnnotationDeleteToUndoStack';
    import { useRemoveTagFromSample } from '$lib/hooks/useRemoveTagFromSample/useRemoveTagFromSample';
    import { page } from '$app/state';
    import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
    import { useRootCollectionOptions } from '$lib/hooks/useRootCollection/useRootCollection';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { Eraser } from '@lucide/svelte';

    const {
        sampleId,
        collection,
        sampleIndex,
        children
    }: {
        sampleId: string;
        collection: Collection;
        sampleIndex?: number;
        children: Snippet | undefined;
    } = $props();

    const {
        getSelectedSampleIds,
        toggleSampleSelection,
        addReversibleAction,
        clearReversibleActions,
        lastAnnotationType
    } = useGlobalStorage();
    const collectionId = collection.collection_id!;
    const selectedSampleIds = getSelectedSampleIds(collectionId);

    // Use our hide annotations hook
    const { isHidden, handleKeyEvent } = useHideAnnotations();
    const { settingsStore } = useSettings();
    const { deleteAnnotation } = useDeleteAnnotation({
        collectionId
    });
    const { deleteCaption } = useDeleteCaption();
    const { removeTagFromSample } = useRemoveTagFromSample({
        collectionId
    });

    // Setup keyboard shortcuts
    // Handle Escape key
    const handleEscape = () => {
        goto(routeHelpers.toSamples(collectionId));
    };

    const { image, refetch } = $derived(useImage({ sampleId }));

    let decodedMasks = new Map<string, Uint8Array>();

    // Populate the decoded masks with the annotations insance segmentation details.
    $effect(() => {
        decodedMasks.clear();

        if (!$image.data) return;

        for (const ann of $image.data.annotations ?? []) {
            const rle = ann.instance_segmentation_details?.segmentation_mask;
            if (!rle) continue;

            decodedMasks.set(
                ann.sample_id,
                decodeRLEToBinaryMask(rle, $image.data.width, $image.data.height)
            );
        }
    });

    const { createAnnotation } = useCreateAnnotation({
        collectionId
    });

    const labels = useAnnotationLabels({ collectionId });
    const { createLabel } = useCreateLabel({ collectionId });
    const { imageBrightness, imageContrast } = page.data.globalStorage;

    const { isEditingMode } = useGlobalStorage();

    let isPanModeEnabled = $state(false);

    const createObjectDetectionAnnotation = async ({
        x,
        y,
        width,
        height,
        labelName
    }: {
        x: number;
        y: number;
        width: number;
        height: number;
        labelName: string;
    }) => {
        if (!$labels.data) {
            return;
        }

        let label = $labels.data.find((label) => label.annotation_label_name === labelName);

        // Create label if it does not exist yet
        if (!label) {
            label = await createLabel({
                annotation_label_name: labelName
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

            if (annotationsToShow.length == 0) {
                refetchRootCollection();
            }

            addAnnotationCreateToUndoStack({
                annotation: newAnnotation,
                addReversibleAction,
                deleteAnnotation,
                refetch
            });

            refetch();

            selectedAnnotationId = newAnnotation.sample_id;

            toast.success('Annotation created successfully');
            return newAnnotation;
        } catch (error) {
            toast.error('Failed to create annotation. Please try again.');
            console.error('Error creating annotation:', error);
            return;
        }
    };

    // Handle keyboard events
    const handleKeyDownEvent = (event: KeyboardEvent) => {
        switch (event.key) {
            // Check for escape key
            case get(settingsStore).key_go_back:
                if ($isEditingMode) {
                    if (addAnnotationEnabled) {
                        addAnnotationEnabled = false;
                    }
                } else {
                    handleEscape();
                }
                break;
            // Add spacebar handling for selection toggle
            case ' ': // Space key
                // Prevent default space behavior (like page scrolling)
                event.preventDefault();
                event.stopPropagation();

                console.log('space pressed in sample details');
                // Toggle selection based on context
                if (!$isEditingMode) {
                    toggleSampleSelection(sampleId, collectionId);
                } else {
                    isPanModeEnabled = true;
                }
                break;
        }

        // Always pass to the hide annotations handler
        handleKeyEvent(event);
    };

    const handleKeyUpEvent = (event: KeyboardEvent) => {
        if (event.key === ' ') {
            isPanModeEnabled = false;
        }
        handleKeyEvent(event);
    };

    let sampleURL = $derived(getImageURL(sampleId));

    let selectedAnnotationId = $state<string>();
    let resetZoomTransform: (() => void) | undefined = $state();

    afterNavigate(() => {
        selectedAnnotationId = undefined;
        boundingBox = undefined;
        // Reset zoom transform when navigating to new sample
        resetZoomTransform?.();
        addAnnotationEnabled = false;
        addAnnotationLabel = undefined;
        clearReversibleActions();
    });

    const toggleAnnotationSelection = (annotationId: string) => {
        if (isPanModeEnabled) return;

        if (selectedAnnotationId === annotationId && !isSegmentationMask) {
            selectedAnnotationId = undefined;
        } else {
            selectedAnnotationId = annotationId;
        }
    };

    let boundingBox = $state<BoundingBox | undefined>();

    let isDragging = $state(false);
    let temporaryBbox = $state<BoundingBox | null>(null);
    let interactionRect: SVGRectElement | null = $state(null);
    let mousePosition = $state<{ x: number; y: number } | null>(null);

    type D3Event = D3DragEvent<SVGRectElement, unknown, unknown>;

    const cancelDrag = () => {
        isDragging = false;
        temporaryBbox = null;
        mousePosition = null;
    };

    let addAnnotationEnabled = $state(false);

    const BOX_MIN_SIZE_PX = 4;
    const setupDragBehavior = () => {
        if (!interactionRect) return;

        const rectSelection = select(interactionRect);

        let startPoint: { x: number; y: number } | null = null;

        // Setup D3 drag behavior for annotation creation
        const dragBehavior = drag<SVGRectElement, unknown>()
            .on('start', (event: D3Event) => {
                if (!addAnnotationEnabled) return;
                isDragging = true;
                // Get mouse position relative to the SVG element
                const svgRect = interactionRect!.getBoundingClientRect();
                const clientX = event.sourceEvent.clientX;
                const clientY = event.sourceEvent.clientY;
                const x = ((clientX - svgRect.left) / svgRect.width) * $image.data!.width;
                const y = ((clientY - svgRect.top) / svgRect.height) * $image.data!.height;

                startPoint = { x, y };
                temporaryBbox = { x, y, width: 0, height: 0 };
                mousePosition = { x, y };
            })
            .on('drag', (event: D3Event) => {
                if (!temporaryBbox || !isDragging || !startPoint) return;

                // Get current mouse position relative to the SVG element
                const svgRect = interactionRect!.getBoundingClientRect();
                const clientX = event.sourceEvent.clientX;
                const clientY = event.sourceEvent.clientY;
                let currentX = ((clientX - svgRect.left) / svgRect.width) * $image.data!.width;
                let currentY = ((clientY - svgRect.top) / svgRect.height) * $image.data!.height;

                // Constrain current position to image bounds
                const imageWidth = $image.data!.width;
                const imageHeight = $image.data!.height;
                currentX = Math.max(0, Math.min(currentX, imageWidth));
                currentY = Math.max(0, Math.min(currentY, imageHeight));

                const x = Math.min(startPoint.x, currentX);
                const y = Math.min(startPoint.y, currentY);
                const width = Math.abs(currentX - startPoint.x);
                const height = Math.abs(currentY - startPoint.y);

                temporaryBbox = { x, y, width, height };
                mousePosition = { x: currentX, y: currentY };
            })
            .on('end', () => {
                if (!temporaryBbox || !isDragging) return;

                // Only create annotation if the rectangle has meaningful size (> 10px in both dimensions)
                if (
                    temporaryBbox.width > BOX_MIN_SIZE_PX &&
                    temporaryBbox.height > BOX_MIN_SIZE_PX
                ) {
                    if (addAnnotationLabel) {
                        createObjectDetectionAnnotation({
                            x: temporaryBbox.x,
                            y: temporaryBbox.y,
                            width: temporaryBbox.width,
                            height: temporaryBbox.height,
                            labelName: addAnnotationLabel.label
                        });
                    }
                }

                cancelDrag();
                startPoint = null;
            });

        if (!isSegmentationMask) rectSelection.call(dragBehavior);

        rectSelection.on('mousemove', trackMousePosition);

        // Return cleanup function
        return () => {
            dragBehavior.on('start', null).on('drag', null).on('end', null);
        };
    };

    const trackMousePositionOrig = (event: MouseEvent) => {
        if (!interactionRect || isDragging) return;

        const svgRect = interactionRect.getBoundingClientRect();
        const clientX = event.clientX;
        const clientY = event.clientY;
        const x = ((clientX - svgRect.left) / svgRect.width) * $image.data!.width;
        const y = ((clientY - svgRect.top) / svgRect.height) * $image.data!.height;

        mousePosition = { x, y };
        event.stopPropagation();
        event.preventDefault();
    };

    const trackMousePosition = _.throttle(trackMousePositionOrig, 50);

    // Setup drag behavior when rect becomes available or mode changes
    $effect(() => {
        setupDragBehavior();

        image.subscribe((result: QueryObserverResult<ImageView>) => {
            if (result.isSuccess && result.data) {
                let annotations = getAnnotations(result.data.annotations);

                annotationsToShow = annotations;
            } else {
                annotationsToShow = [];
            }
        });
    });

    let addAnnotationLabel = $state<ListItem | undefined>(undefined);

    let annotationsToShow = $state<AnnotationView[]>([]);

    let annotationsIdsToHide = $state<Set<string>>(new Set());

    const onToggleShowAnnotation = (annotationId: string) => {
        const newSet = new Set(annotationsIdsToHide);
        if (newSet.has(annotationId)) {
            newSet.delete(annotationId);
        } else {
            newSet.add(annotationId);
        }
        annotationsIdsToHide = newSet;
    };

    const actualAnnotationsToShow = $derived.by(() => {
        return annotationsToShow.filter(
            (annotation: AnnotationView) => !annotationsIdsToHide.has(annotation.sample_id)
        );
    });

    const drawerStrokeColor = $derived(
        addAnnotationLabel ? getColorByLabel(addAnnotationLabel.label, 1).color : 'blue'
    );

    const handleDeleteAnnotation = async (annotationId: string) => {
        if (!$image.data || !$labels.data) return;

        const annotation = $image.data.annotations?.find((a) => a.sample_id === annotationId);
        if (!annotation) return;

        const _delete = async () => {
            try {
                addAnnotationDeleteToUndoStack({
                    annotation,
                    labels: $labels.data!,
                    addReversibleAction,
                    createAnnotation,
                    refetch
                });

                await deleteAnnotation(annotationId);
                toast.success('Annotation deleted successfully');
                refetch();
                if (selectedAnnotationId === annotationId) {
                    selectedAnnotationId = undefined;
                }
            } catch (error) {
                toast.error('Failed to delete annotation. Please try again.');
                console.error('Error deleting annotation:', error);
            }
        };
        _delete();
    };

    const handleDeleteCaption = async (sampleId: string) => {
        if (!$image.data) return;

        try {
            await deleteCaption(sampleId);
            toast.success('Caption deleted successfully');
            refetch();
        } catch (error) {
            toast.error('Failed to delete caption. Please try again.');
            console.error('Error deleting caption:', error);
        }
    };

    const handleRemoveTag = async (tagId: string) => {
        try {
            await removeTagFromSample(sampleId, tagId);
            toast.success('Tag removed successfully');
            refetch();
        } catch (error) {
            toast.error('Failed to remove tag. Please try again.');
            console.error('Error removing tag from sample:', error);
        }
    };

    const { createCaption } = useCreateCaption();
    const { rootCollection, refetch: refetchRootCollection } = useRootCollectionOptions({
        collectionId
    });

    const onCreateCaption = async (sampleId: string) => {
        try {
            await createCaption({ parent_sample_id: sampleId });
            toast.success('Caption created successfully');
            refetch();

            if (!$image.captions) refetchRootCollection();
        } catch (error) {
            toast.error('Failed to create caption. Please try again.');
            console.error('Error creating caption:', error);
        }
    };

    const cursor = $derived.by(() => {
        if (!isEditingMode) return 'auto';
        if (isEraser) return 'auto';
        if (isPanModeEnabled) return 'grab';
        return isDrawingEnabled ? 'crosshair' : 'auto';
    });

    const isResizable = $derived($isEditingMode && !isPanModeEnabled);
    const isDrawingEnabled = $derived(
        addAnnotationEnabled && !isPanModeEnabled && addAnnotationLabel !== undefined
    );

    let htmlContainer: HTMLDivElement | null = $state(null);

    let isDrawingSegmentation = $state(false);
    let segmentationPath = $state<{ x: number; y: number }[]>([]);
    let annotationType = $state<string | null>(
        $lastAnnotationType[collectionId] ?? AnnotationType.OBJECT_DETECTION
    );
    let isSegmentationMask = $derived(annotationType == AnnotationType.INSTANCE_SEGMENTATION);

    const canDrawSegmentation = $derived(isSegmentationMask && addAnnotationEnabled);

    // Define the bounding box given a segmentation mask.
    const computeBoundingBoxFromMask = (
        mask: Uint8Array,
        imageWidth: number,
        imageHeight: number
    ): BoundingBox | null => {
        let minX = imageWidth;
        let minY = imageHeight;
        let maxX = -1;
        let maxY = -1;

        for (let y = 0; y < imageHeight; y++) {
            for (let x = 0; x < imageWidth; x++) {
                if (mask[y * imageWidth + x] === 1) {
                    minX = Math.min(minX, x);
                    minY = Math.min(minY, y);
                    maxX = Math.max(maxX, x);
                    maxY = Math.max(maxY, y);
                }
            }
        }

        if (maxX < minX || maxY < minY) return null;

        return {
            x: minX,
            y: minY,
            width: maxX - minX + 1,
            height: maxY - minY + 1
        };
    };

    const getImageCoordsFromMouse = (event: MouseEvent) => {
        if (!interactionRect || !$image.data) return null;

        const rect = interactionRect.getBoundingClientRect();

        return {
            x: ((event.clientX - rect.left) / rect.width) * $image.data.width,
            y: ((event.clientY - rect.top) / rect.height) * $image.data.height
        };
    };

    // Append the mouse point to the segmentation path while drawing.
    const continueSegmentationDraw = (event: MouseEvent) => {
        if (!isDrawingSegmentation || !canDrawSegmentation) return;

        const point = getImageCoordsFromMouse(event);

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

    // Converts a 2D polygon into a binary segmentation mask.
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

    // Encode the binary mask into a RLE reprensetation.
    const encodeBinaryMaskToRLE = (mask: Uint8Array): number[] => {
        const rle: number[] = [];
        let lastValue = 0; // background
        let count = 0;

        for (let i = 0; i < mask.length; i++) {
            if (mask[i] === lastValue) {
                count++;
            } else {
                rle.push(count);
                count = 1;
                lastValue = mask[i];
            }
        }

        rle.push(count);
        return rle;
    };

    const createSegmentationRLE = async (polygon: { x: number; y: number }[]) => {
        if (!$image.data || !addAnnotationLabel || !$labels.data) return;

        let label = $labels.data.find((l) => l.annotation_label_name === addAnnotationLabel?.label);

        if (!label) {
            label = await createLabel({
                annotation_label_name: addAnnotationLabel.label
            });
        }

        const imageWidth = $image.data.width;
        const imageHeight = $image.data.height;

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

    const handleSegmentationClick = (event: MouseEvent) => {
        if (!isDrawingSegmentation) {
            const point = getImageCoordsFromMouse(event);
            if (!point) return;

            isDrawingSegmentation = true;
            segmentationPath = [point];
        } else {
            finishSegmentationDraw();
        }
    };

    const withAlpha = (color: string, alpha: number) =>
        color.replace(/rgba?\(([^)]+)\)/, (_, c) => {
            const [r, g, b] = c.split(',').map(Number);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        });

    let isEraser = $state(false);

    let isErasing = $state(false);
    let eraserRadius = $state(5);
    let eraserPath = $state<{ x: number; y: number }[]>([]);

    const decodeRLEToBinaryMask = (rle: number[], width: number, height: number): Uint8Array => {
        const mask = new Uint8Array(width * height);
        let idx = 0;
        let value = 0;

        for (const count of rle) {
            for (let i = 0; i < count; i++) {
                if (idx < mask.length) {
                    mask[idx++] = value;
                }
            }
            value = value === 0 ? 1 : 0;
        }

        return mask;
    };

    // Apply the eraser to the mask at the eraser cursor is position.
    const applyEraserToMask = (
        mask: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        path: { x: number; y: number }[],
        radius: number,
        value: 0 | 1
    ) => {
        const r2 = radius * radius;

        for (const p of path) {
            const cx = Math.round(p.x);
            const cy = Math.round(p.y);

            const minX = Math.max(0, cx - radius);
            const maxX = Math.min(imageWidth - 1, cx + radius);
            const minY = Math.max(0, cy - radius);
            const maxY = Math.min(imageHeight - 1, cy + radius);

            for (let y = minY; y <= maxY; y++) {
                for (let x = minX; x <= maxX; x++) {
                    const dx = x - cx;
                    const dy = y - cy;
                    if (dx * dx + dy * dy <= r2) {
                        mask[y * imageWidth + x] = value;
                    }
                }
            }
        }
    };

    const { updateAnnotation } = $derived(
        useAnnotation({
            collectionId,
            annotationId: selectedAnnotationId!
        })
    );

    const finishEraser = async () => {
        isErasing = false;

        if (!selectedAnnotationId) {
            return toast.info('Please, select an annotation first.');
        }

        if (eraserPath.length === 0 || !$image.data) {
            eraserPath = [];
            return;
        }

        const annotation = $image.data.annotations?.find(
            (a) => a.sample_id === selectedAnnotationId
        );
        const rle = annotation?.instance_segmentation_details?.segmentation_mask;
        if (!rle) {
            toast.error('No segmentation mask to edit');
            eraserPath = [];
            return;
        }

        const imageWidth = $image.data.width;
        const imageHeight = $image.data.height;

        // Decode
        const mask = decodeRLEToBinaryMask(rle, imageWidth, imageHeight);

        // Apply: add => 1, erase => 0
        const writeValue: 0 | 1 = isEraser ? 0 : 1;
        applyEraserToMask(mask, imageWidth, imageHeight, eraserPath, eraserRadius, writeValue);

        // Recompute bbox
        const bbox = computeBoundingBoxFromMask(mask, imageWidth, imageHeight);
        if (!bbox) {
            toast.error('Mask is empty after edit');
            eraserPath = [];
            return;
        }

        const newRLE = encodeBinaryMaskToRLE(mask);

        await updateAnnotation({
            annotation_id: selectedAnnotationId,
            collection_id: collectionId,
            segmentation_mask: newRLE,
            bounding_box: bbox
        });

        refetch();
        eraserPath = [];
    };

    $effect(() => {
        if (!$isEditingMode) {
            isEraser = false;
            isErasing = false;
        }
    });

    const findAnnotationAtPoint = (x: number, y: number): string | null => {
        if (!$image.data) return null;

        const ix = Math.round(x);
        const iy = Math.round(y);
        const w = $image.data.width;
        const idx = iy * w + ix;

        // Iterate in reverse draw order
        const anns = [...($image.data.annotations ?? [])].reverse();

        for (const ann of anns) {
            const mask = decodedMasks.get(ann.sample_id);
            if (!mask) continue;

            if (mask[idx] === 1) {
                return ann.sample_id;
            }
        }

        return null;
    };
</script>

{#if $image.data}
    <div class="flex h-full w-full flex-col space-y-4">
        <div class="flex w-full items-center justify-between">
            {#if $rootCollection.data}
                <SampleDetailsBreadcrumb rootCollection={$rootCollection.data} {sampleIndex} />
            {/if}
            {#if $isEditingMode}
                <ImageAdjustments
                    bind:brightness={$imageBrightness}
                    bind:contrast={$imageContrast}
                />
            {/if}
        </div>
        <Separator class="bg-border-hard" />

        <div class="flex min-h-0 flex-1 gap-4">
            {#if $isEditingMode}
                <Card>
                    <CardContent>
                        <button
                            type="button"
                            aria-label="Toggle eraser"
                            disabled={!$isEditingMode}
                            onclick={() => (isEraser = !isEraser)}
                            class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none 
        ${isEraser ? 'bg-black/40' : 'hover:bg-black/20'}
    `}
                        >
                            <Eraser
                                class={`
            size-4
            ${$isEditingMode ? 'hover:text-primary' : ''}
            ${isEraser ? 'text-primary' : ''}
        `}
                        />
                    </button>
                </CardContent>
            </Card>
            <div class="flex-1">
                <Card className="h-full">
                    <CardContent className="h-full">
                        <div class="h-full w-full overflow-hidden">
                            <div class="sample relative h-full w-full" bind:this={htmlContainer}>
                                <div class="absolute right-4 top-2 z-30 flex items-center gap-2">
                                    <SelectableBox
                                        onSelect={() =>
                                            toggleSampleSelection(sampleId, collectionId)}
                                        isSelected={$selectedSampleIds.has(sampleId)}
                                    />
                                </div>

                                {#if children}
                                    {@render children()}
                                {/if}

                                <ZoomableContainer
                                    width={$image.data.width}
                                    height={$image.data.height}
                                    {cursor}
                                    {boundingBox}
                                    panEnabled={!isErasing}
                                    registerResetFn={(fn) => (resetZoomTransform = fn)}
                                >
                                    {#snippet zoomableContent()}
                                        <image
                                            href={sampleURL}
                                            style={`filter: brightness(${$imageBrightness}) contrast(${$imageContrast})`}
                                        />

                                        {#if $image.data}
                                            <g class:invisible={$isHidden}>
                                                {#each actualAnnotationsToShow as annotation (annotation.sample_id)}
                                                    <SampleDetailsAnnotation
                                                        annotationId={annotation.sample_id}
                                                        {sampleId}
                                                        {collectionId}
                                                        {isResizable}
                                                        isSelected={selectedAnnotationId ===
                                                            annotation.sample_id}
                                                        {toggleAnnotationSelection}
                                                    />
                                                {/each}

                                                {#if temporaryBbox && isDragging && addAnnotationLabel}
                                                    <ResizableRectangle
                                                        bbox={temporaryBbox}
                                                        colorStroke={drawerStrokeColor}
                                                        colorFill="rgba(0, 123, 255, 0.1)"
                                                        style="outline: 0;"
                                                        opacity={0.8}
                                                        scale={1}
                                                    />
                                                {/if}
                                                {#if isErasing && eraserPath.length}
                                                    <circle
                                                        cx={eraserPath[eraserPath.length - 1].x}
                                                        cy={eraserPath[eraserPath.length - 1].y}
                                                        r={eraserRadius}
                                                        fill="rgba(255,255,255,0.2)"
                                                        stroke="white"
                                                    />
                                                {/if}
                                                {#if mousePosition && isDrawingEnabled && $isEditingMode && !isEraser}
                                                    <!-- Horizontal crosshair line -->
                                                    <line
                                                        x1="0"
                                                        y1={mousePosition.y}
                                                        x2={$image.data.width}
                                                        y2={mousePosition.y}
                                                        stroke={drawerStrokeColor}
                                                        stroke-width="1"
                                                        vector-effect="non-scaling-stroke"
                                                        stroke-dasharray="5,5"
                                                        opacity="0.6"
                                                    />
                                                    <!-- Vertical crosshair line -->
                                                    <line
                                                        x1={mousePosition.x}
                                                        y1="0"
                                                        x2={mousePosition.x}
                                                        y2={$image.data.height}
                                                        stroke={drawerStrokeColor}
                                                        stroke-width="1"
                                                        stroke-dasharray="5,5"
                                                        opacity="0.6"
                                                    />
                                                {/if}
                                            </g>
                                            {#if segmentationPath.length > 1 && addAnnotationLabel}
                                                <path
                                                    d={`M ${segmentationPath.map((p) => `${p.x},${p.y}`).join(' L ')}`}
                                                    fill={withAlpha(drawerStrokeColor, 0.08)}
                                                    stroke={drawerStrokeColor}
                                                    stroke-width="2"
                                                    vector-effect="non-scaling-stroke"
                                                />
                                            {/if}
                                            {#if (isDrawingEnabled || isEraser) && $isEditingMode}
                                                <rect
                                                    bind:this={interactionRect}
                                                    width={$image.data.width}
                                                    height={$image.data.height}
                                                    fill="transparent"
                                                    style={`outline: 0; cursor: ${isEraser ? 'auto' : 'crosshair'}`}
                                                    tabindex="0"
                                                    role="button"
                                                    onpointerdown={(e) => {
                                                        if (!isEraser) return;
                                                        const p = getImageCoordsFromMouse(e);
                                                        if (!p) return;
                                                        isErasing = true;
                                                        const hitAnnotationId =
                                                            findAnnotationAtPoint(p.x, p.y);

                                                        if (!hitAnnotationId) return;

                                                        selectedAnnotationId = hitAnnotationId;
                                                        eraserPath = [p];
                                                    }}
                                                    onpointermove={(e) => {
                                                        if (isEraser) {
                                                            if (!isErasing) return;

                                                            const p = getImageCoordsFromMouse(e);
                                                            if (p) eraserPath = [...eraserPath, p];
                                                        } else {
                                                            if (!isSegmentationMask) return;

                                                            continueSegmentationDraw(e);
                                                        }
                                                    }}
                                                    onpointerup={() => {
                                                        if (isEraser && isErasing) {
                                                            finishEraser();
                                                        }
                                                    }}
                                                    onmouseleave={() => {
                                                        if (isEraser && isErasing) {
                                                            finishEraser();
                                                        } else if (
                                                            !isEraser &&
                                                            isSegmentationMask
                                                        ) {
                                                            finishSegmentationDraw();
                                                        }
                                                    }}
                                                    onclick={(e) => {
                                                        if (!isSegmentationMask || isEraser) return;
                                                        handleSegmentationClick(e);
                                                    }}
                                                    onkeydown={(e) => {
                                                        if (!isSegmentationMask || isEraser) return;

                                                        if (e.key === 'Enter' || e.key === ' ') {
                                                            e.preventDefault();
                                                            handleSegmentationClick(
                                                                e as unknown as MouseEvent
                                                            );
                                                        }
                                                    }}
                                                />
                                            {/if}
                                        {/if}
                                    {/snippet}
                                </ZoomableContainer>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
            <div class="relative w-[375px]">
                {#if $image.data}
                    <SampleDetailsSidePanel
                        bind:addAnnotationEnabled
                        bind:addAnnotationLabel
                        sample={$image.data}
                        {annotationsIdsToHide}
                        {selectedAnnotationId}
                        onAnnotationClick={toggleAnnotationSelection}
                        {onToggleShowAnnotation}
                        onDeleteAnnotation={handleDeleteAnnotation}
                        onDeleteCaption={handleDeleteCaption}
                        {onCreateCaption}
                        onRemoveTag={handleRemoveTag}
                        onUpdate={refetch}
                        bind:annotationType
                        {collectionId}
                    />
                {/if}
            </div>
        </div>
    </div>
{:else}
    <div data-testid="sample-details-loading">
        <Spinner />
    </div>
{/if}

<svelte:window onkeydown={handleKeyDownEvent} onkeyup={handleKeyUpEvent} />
