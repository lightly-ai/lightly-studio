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
    import { select } from 'd3-selection';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import type { ListItem } from '../SelectList/types';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { getColorByLabel } from '$lib/utils';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { useDeleteCaption } from '$lib/hooks/useDeleteCaption/useDeleteCaption';
    import { addAnnotationDeleteToUndoStack } from '$lib/services/addAnnotationDeleteToUndoStack';
    import { useRemoveTagFromSample } from '$lib/hooks/useRemoveTagFromSample/useRemoveTagFromSample';
    import { page } from '$app/state';
    import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
    import { useRootCollectionOptions } from '$lib/hooks/useRootCollection/useRootCollection';
    import SampleInstanceSegmentationRect from './SampleInstanceSegmentationRect/SampleInstanceSegmentationRect.svelte';
    import SampleEraserRect from './SampleEraserRect/SampleEraserRect.svelte';
    import SampleObjectDetectionRect from './SampleObjectDetectionRect/SampleObjectDetectionRect.svelte';
    import SampleDetailsToolbar from './SampleDetailsToolbar/SampleDetailsToolbar.svelte';

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
        lastAnnotationType,
        lastAnnotationBrushSize
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

    const { createAnnotation } = useCreateAnnotation({
        collectionId
    });

    const labels = useAnnotationLabels({ collectionId });
    const { imageBrightness, imageContrast } = page.data.globalStorage;

    const { isEditingMode } = useGlobalStorage();

    let isPanModeEnabled = $state(false);

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
    let interactionRect: SVGRectElement | null = $state(null);
    let mousePosition = $state<{ x: number; y: number } | null>(null);
    let addAnnotationEnabled = $state(false);

    const setupMouseMonitor = () => {
        if (!interactionRect) return;

        const rectSelection = select(interactionRect);

        rectSelection.on('mousemove', trackMousePosition);
    };

    const trackMousePositionOrig = (event: MouseEvent) => {
        if (!interactionRect) return;

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

    $effect(() => {
        setupMouseMonitor();

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
    let segmentationPath = $state<{ x: number; y: number }[]>([]);
    let annotationType = $state<string | null>(
        $lastAnnotationType[collectionId] ?? AnnotationType.OBJECT_DETECTION
    );
    let isSegmentationMask = $derived(annotationType == AnnotationType.INSTANCE_SEGMENTATION);
    const canDrawSegmentation = $derived(isSegmentationMask && addAnnotationEnabled);

    let isEraser = $state(false);
    let isErasing = $state(false);

    $effect(() => {
        if (!$isEditingMode) {
            isEraser = false;
            isErasing = false;
        }
    });

    let brushRadius = $state($lastAnnotationBrushSize[collectionId] ?? 2);
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
                <SampleDetailsToolbar bind:isEraser bind:brushRadius {collectionId} />
            {/if}
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
                                            {#if $isEditingMode}
                                                {#if isEraser}
                                                    <SampleEraserRect
                                                        bind:interactionRect
                                                        bind:isErasing
                                                        {selectedAnnotationId}
                                                        {collectionId}
                                                        {brushRadius}
                                                        {refetch}
                                                        sample={{
                                                            width: $image.data.width,
                                                            height: $image.data.height,
                                                            annotations: $image.data.annotations
                                                        }}
                                                    />
                                                {:else if canDrawSegmentation}
                                                    <SampleInstanceSegmentationRect
                                                        bind:interactionRect
                                                        {segmentationPath}
                                                        {sampleId}
                                                        {collectionId}
                                                        {brushRadius}
                                                        {refetch}
                                                        {drawerStrokeColor}
                                                        draftAnnotationLabel={addAnnotationLabel}
                                                        sample={{
                                                            width: $image.data.width,
                                                            height: $image.data.height
                                                        }}
                                                    />
                                                {:else if isDrawingEnabled}
                                                    <SampleObjectDetectionRect
                                                        bind:interactionRect
                                                        bind:selectedAnnotationId
                                                        sample={{
                                                            width: $image.data.width,
                                                            height: $image.data.height,
                                                            annotations: annotationsToShow
                                                        }}
                                                        {sampleId}
                                                        {collectionId}
                                                        draftAnnotationLabel={addAnnotationLabel}
                                                        {drawerStrokeColor}
                                                        {refetch}
                                                    />
                                                {/if}
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
