<script lang="ts">
    import { afterNavigate, goto } from '$app/navigation';
    import { Card, CardContent, SampleDetailsSidePanel, SelectableBox } from '$lib/components';
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
    import { useSample } from '$lib/hooks/useSample/useSample';
    import type { Dataset } from '$lib/services/types';
    import { getAnnotations } from '../SampleAnnotation/utils';
    import Spinner from '../Spinner/Spinner.svelte';
    import type { AnnotationView, SampleView } from '$lib/api/lightly_studio_local';
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
    import { useRemoveTagFromSample } from '$lib/hooks/useRemoveTagFromSample/useRemoveTagFromSample';
    import { page } from '$app/state';

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

    const { selectedSampleIds, toggleSampleSelection } = useGlobalStorage();
    const datasetId = dataset.dataset_id!;

    // Use our hide annotations hook
    const { isHidden, handleKeyEvent } = useHideAnnotations();
    const { settingsStore } = useSettings();
    const { deleteAnnotation } = useDeleteAnnotation({
        datasetId
    });
    const { removeTagFromSample } = useRemoveTagFromSample({
        datasetId
    });

    // Setup keyboard shortcuts
    // Handle Escape key
    const handleEscape = () => {
        goto(routeHelpers.toSamples(datasetId));
    };

    const { sample, refetch } = $derived(
        useSample({
            sampleId,
            datasetId
        })
    );

    const { createAnnotation } = useCreateAnnotation({
        datasetId
    });

    const labels = useAnnotationLabels();
    const { createLabel } = useCreateLabel();
    const { isEditingMode } = page.data.globalStorage;

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
                sample_id: sampleId,
                annotation_type: 'object_detection',
                x: Math.round(x),
                y: Math.round(y),
                width: Math.round(width),
                height: Math.round(height),
                annotation_label_id: label.annotation_label_id!
            });

            refetch();

            selectedAnnotationId = newAnnotation.annotation_id;

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
                handleEscape();
                break;
            // Add spacebar handling for selection toggle
            case ' ': // Space key
                // Prevent default space behavior (like page scrolling)
                event.preventDefault();
                event.stopPropagation();

                console.log('space pressed in sample details');
                // Toggle selection based on context
                if (!$isEditingMode) {
                    toggleSampleSelection(sampleId);
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
    });

    const toggleAnnotationSelection = (annotationId: string) => {
        if (isPanModeEnabled) return;

        if (selectedAnnotationId === annotationId) {
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

    const BOX_MIN_SIZE_PX = 10;
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
                const x = ((clientX - svgRect.left) / svgRect.width) * $sample.data!.width;
                const y = ((clientY - svgRect.top) / svgRect.height) * $sample.data!.height;

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
                let currentX = ((clientX - svgRect.left) / svgRect.width) * $sample.data!.width;
                let currentY = ((clientY - svgRect.top) / svgRect.height) * $sample.data!.height;

                // Constrain current position to image bounds
                const imageWidth = $sample.data!.width;
                const imageHeight = $sample.data!.height;
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
        const x = ((clientX - svgRect.left) / svgRect.width) * $sample.data!.width;
        const y = ((clientY - svgRect.top) / svgRect.height) * $sample.data!.height;

        mousePosition = { x, y };
        event.stopPropagation();
        event.preventDefault();
    };

    const trackMousePosition = _.throttle(trackMousePositionOrig, 50);

    // Setup drag behavior when rect becomes available or mode changes
    $effect(() => {
        setupDragBehavior();

        sample.subscribe((result: QueryObserverResult<SampleView>) => {
            if (result.isSuccess && result.data) {
                let annotations = getAnnotations(result.data);

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
            (annotation: AnnotationView) => !annotationsIdsToHide.has(annotation.annotation_id)
        );
    });

    const drawerStrokeColor = $derived(
        addAnnotationLabel ? getColorByLabel(addAnnotationLabel.label, 1).color : 'blue'
    );

    const handleDeleteAnnotation = async (annotationId: string) => {
        if (!$sample.data) return;

        const _delete = async () => {
            try {
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
</script>

{#if $sample.data}
    <div class="flex h-full w-full flex-col space-y-4">
        <div class="flex w-full items-center">
            <SampleDetailsBreadcrumb {dataset} {sampleIndex} />
        </div>
        <Separator class="mb-4 bg-border-hard" />
        <div class="flex min-h-0 flex-1 gap-4">
            <div class="flex-1">
                <Card className="h-full">
                    <CardContent className="h-full">
                        <div class="h-full w-full overflow-hidden">
                            <div class="sample relative h-full w-full" bind:this={htmlContainer}>
                                <div class="absolute right-4 top-2 z-30">
                                    <SelectableBox
                                        onSelect={() => toggleSampleSelection(sampleId)}
                                        isSelected={$selectedSampleIds.has(sampleId)}
                                    />
                                </div>

                                {#if children}
                                    {@render children()}
                                {/if}

                                <ZoomableContainer
                                    width={$sample.data.width}
                                    height={$sample.data.height}
                                    {cursor}
                                    {boundingBox}
                                    registerResetFn={(fn) => (resetZoomTransform = fn)}
                                >
                                    {#snippet zoomableContent()}
                                        <image href={sampleURL} />

                                        {#if $sample.data}
                                            <g class:invisible={$isHidden}>
                                                {#each actualAnnotationsToShow as annotation (annotation.annotation_id)}
                                                    <SampleDetailsAnnotation
                                                        annotationId={annotation.annotation_id}
                                                        {sampleId}
                                                        {datasetId}
                                                        {isResizable}
                                                        isSelected={selectedAnnotationId ===
                                                            annotation.annotation_id}
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

                                                {#if mousePosition && isDrawingEnabled}
                                                    <!-- Horizontal crosshair line -->
                                                    <line
                                                        x1="0"
                                                        y1={mousePosition.y}
                                                        x2={$sample.data.width}
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
                                                        y2={$sample.data.height}
                                                        vector-effect="non-scaling-stroke"
                                                        stroke={drawerStrokeColor}
                                                        stroke-width="1"
                                                        stroke-dasharray="5,5"
                                                        opacity="0.6"
                                                    />
                                                {/if}
                                            </g>
                                            {#if isDrawingEnabled}
                                                <rect
                                                    bind:this={interactionRect}
                                                    width={$sample.data.width}
                                                    height={$sample.data.height}
                                                    class="select-none"
                                                    fill="transparent"
                                                    role="button"
                                                    style="outline: 0;cursor: crosshair;"
                                                    tabindex="0"
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
                {#if $sample.data}
                    <SampleDetailsSidePanel
                        bind:addAnnotationEnabled
                        bind:addAnnotationLabel
                        sample={$sample.data}
                        {annotationsIdsToHide}
                        {selectedAnnotationId}
                        onAnnotationClick={toggleAnnotationSelection}
                        {onToggleShowAnnotation}
                        onDeleteAnnotation={handleDeleteAnnotation}
                        onRemoveTag={handleRemoveTag}
                        onUpdate={refetch}
                    />
                {/if}
            </div>
        </div>
    </div>
{:else}
    <Spinner />
{/if}

<svelte:window onkeydown={handleKeyDownEvent} onkeyup={handleKeyUpEvent} />
