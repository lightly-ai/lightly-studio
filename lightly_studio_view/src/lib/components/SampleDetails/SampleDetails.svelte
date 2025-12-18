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
    import type { Dataset } from '$lib/services/types';
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
    import { useRootDatasetOptions } from '$lib/hooks/useRootDataset/useRootDataset';

    const {
        sampleId,
        dataset,
        sampleIndex,
        children
    }: {
        sampleId: string;
        dataset: Dataset;
        sampleIndex?: number;
        children: Snippet | undefined;
    } = $props();

    const {
        getSelectedSampleIds,
        toggleSampleSelection,
        addReversibleAction,
        clearReversibleActions
    } = useGlobalStorage();
    const datasetId = dataset.dataset_id!;
    const selectedSampleIds = getSelectedSampleIds(datasetId);

    // Use our hide annotations hook
    const { isHidden, handleKeyEvent } = useHideAnnotations();
    const { settingsStore } = useSettings();
    const { deleteAnnotation } = useDeleteAnnotation({
        datasetId
    });
    const { deleteCaption } = useDeleteCaption();
    const { removeTagFromSample } = useRemoveTagFromSample({
        datasetId
    });

    // Setup keyboard shortcuts
    // Handle Escape key
    const handleEscape = () => {
        goto(routeHelpers.toSamples(datasetId));
    };

    const { image, refetch } = $derived(useImage({ sampleId }));

    const { createAnnotation } = useCreateAnnotation({
        datasetId
    });

    const labels = useAnnotationLabels({ datasetId });
    const { createLabel } = useCreateLabel({ datasetId });
    const { isEditingMode, imageBrightness, imageContrast } = page.data.globalStorage;

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
                refetchRootDataset();
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
                    toggleSampleSelection(sampleId, datasetId);
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
                activeBbox = {
                    x: Math.round(x),
                    y: Math.round(y),
                    width: Math.round(width),
                    height: Math.round(height)
                };
                mousePosition = { x: currentX, y: currentY };
            })
            .on('end', () => {
                if (!temporaryBbox || !isDragging || isSegmentationMask) return;

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

        rectSelection.call(dragBehavior);

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
    const { rootDataset, refetch: refetchRootDataset } = useRootDatasetOptions({ datasetId });

    const onCreateCaption = async (sampleId: string) => {
        try {
            await createCaption({ parent_sample_id: sampleId });
            toast.success('Caption created successfully');
            refetch();

            if (!$image.captions) refetchRootDataset();
        } catch (error) {
            toast.error('Failed to create caption. Please try again.');
            console.error('Error creating caption:', error);
        }
    };

    const cursor = $derived.by(() => {
        if (isPanModeEnabled) {
            return 'grab';
        }
        return isDrawingEnabled ? 'crosshair' : 'auto';
    });

    const isResizable = $derived($isEditingMode && !isPanModeEnabled);
    const isDrawingEnabled = $derived(
        addAnnotationEnabled && !isPanModeEnabled && addAnnotationLabel !== undefined
    );

    let htmlContainer: HTMLDivElement | null = $state(null);

    let isDrawingSegmentation = $state(false);
    let segmentationPath = $state<{ x: number; y: number }[]>([]);
    let activeBbox = $state<BoundingBox | null>(null);
    let annotationType = $state<string | null>(AnnotationType.OBJECT_DETECTION);
    let isSegmentationMask = $derived(annotationType == AnnotationType.INSTANCE_SEGMENTATION);

    const canDrawSegmentation = $derived(isSegmentationMask && addAnnotationEnabled && activeBbox);

    const getImageCoordsFromMouse = (event: MouseEvent) => {
        if (!interactionRect || !$image.data) return null;

        const rect = interactionRect.getBoundingClientRect();

        return {
            x: ((event.clientX - rect.left) / rect.width) * $image.data.width,
            y: ((event.clientY - rect.top) / rect.height) * $image.data.height
        };
    };

    const continueSegmentationDraw = (event: MouseEvent) => {
        if (!isDrawingSegmentation || !canDrawSegmentation || !activeBbox) return;

        const point = getImageCoordsFromMouse(event);
        if (!point) return;

        const { x, y, width, height } = activeBbox;

        if (point.x < x || point.y < y || point.x > x + width || point.y > y + height) {
            return; // outside bbox
        }

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
        if (!$image.data || !addAnnotationLabel || !$labels.data || !activeBbox) return;

        let label = $labels.data.find((l) => l.annotation_label_name === addAnnotationLabel?.label);
        if (!label) {
            label = await createLabel({
                annotation_label_name: addAnnotationLabel?.label
            });
        }

        const mask = rasterizePolygonToMask(polygon, $image.data.width, $image.data.height);

        const rle = encodeBinaryMaskToRLE(mask);

        await createAnnotation({
            parent_sample_id: sampleId,
            annotation_type: 'instance_segmentation',
            x: activeBbox.x,
            y: activeBbox.y,
            width: activeBbox.width,
            height: activeBbox.height,
            segmentation_mask: rle,
            annotation_label_id: label.annotation_label_id!
        });

        refetch();
    };

    const handleSegmentationClick = (event: MouseEvent) => {
        if (!canDrawSegmentation) {
            toast.info('Draw or select a bounding box first.');
            return;
        }

        if (!isDrawingSegmentation) {
            const point = getImageCoordsFromMouse(event);
            if (!point) return;

            // Ensure first point is inside bbox
            const { x, y, width, height } = activeBbox!;
            if (point.x < x || point.y < y || point.x > x + width || point.y > y + height) {
                return;
            }

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
</script>

{#if $image.data}
    <div class="flex h-full w-full flex-col space-y-4">
        <div class="flex w-full items-center justify-between">
            {#if $rootDataset.data}
                <SampleDetailsBreadcrumb rootDataset={$rootDataset.data} {sampleIndex} />
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
            <div class="flex-1">
                <Card className="h-full">
                    <CardContent className="h-full">
                        <div class="h-full w-full overflow-hidden">
                            <div class="sample relative h-full w-full" bind:this={htmlContainer}>
                                <div class="absolute right-4 top-2 z-30">
                                    <SelectableBox
                                        onSelect={() => toggleSampleSelection(sampleId, datasetId)}
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
                                                        {datasetId}
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
                                                {#if isSegmentationMask && activeBbox && addAnnotationLabel}
                                                    <ResizableRectangle
                                                        bbox={activeBbox}
                                                        colorStroke={drawerStrokeColor}
                                                        colorFill={withAlpha(
                                                            drawerStrokeColor,
                                                            0.8
                                                        )}
                                                        scale={1}
                                                    />
                                                {/if}

                                                {#if mousePosition && isDrawingEnabled}
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
                                            {#if isDrawingEnabled}
                                                <rect
                                                    bind:this={interactionRect}
                                                    width={$image.data.width}
                                                    height={$image.data.height}
                                                    class="select-none"
                                                    fill="transparent"
                                                    role="button"
                                                    style="outline: 0;cursor: crosshair;"
                                                    tabindex="0"
                                                    onclick={isSegmentationMask
                                                        ? handleSegmentationClick
                                                        : null}
                                                    onmousemove={isSegmentationMask
                                                        ? continueSegmentationDraw
                                                        : null}
                                                    onmouseleave={isSegmentationMask
                                                        ? finishSegmentationDraw
                                                        : null}
                                                    onkeydown={(e) => {
                                                        if (!isSegmentationMask) return;

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
                        {datasetId}
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
