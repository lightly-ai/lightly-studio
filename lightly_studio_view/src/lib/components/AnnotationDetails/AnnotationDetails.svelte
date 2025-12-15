<script lang="ts">
    import { afterNavigate, beforeNavigate, goto } from '$app/navigation';
    import { Card, CardContent, SampleAnnotation, SelectableBox } from '$lib/components';
    import { ImageAdjustments } from '$lib/components/ImageAdjustments';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useSettings } from '$lib/hooks/useSettings';
    import { routeHelpers } from '$lib/routes';
    import AnnotationDetailsNavigation from '$lib/components/AnnotationDetails/AnnotationDetailsNavigation/AnnotationDetailsNavigation.svelte';
    import { get } from 'svelte/store';
    import AnnotationDetailsPanel from './AnnotationDetailsPanel/AnnotationDetailsPanel.svelte';
    import AnnotationDetailsBreadcrumb from './AnnotationDetailsBreadcrumb/AnnotationDetailsBreadcrumb.svelte';
    import type { Dataset, ImageSample } from '$lib/services/types';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useRootDatasetOptions } from '$lib/hooks/useRootDataset/useRootDataset';
    import { page } from '$app/state';
    import { ZoomableContainer } from '$lib/components';
    import { getImageURL } from '$lib/utils/getImageURL';
    import { getBoundingBox } from '../SampleAnnotation/utils';
    import Spinner from '../Spinner/Spinner.svelte';
    import type { BoundingBox } from '$lib/types';
    import { toast } from 'svelte-sonner';
    import { addAnnotationUpdateToUndoStack } from '$lib/services/addAnnotationUpdateToUndoStack';

    const {
        toggleSampleAnnotationCropSelection,
        selectedSampleAnnotationCropIds,
        clearReversibleActions,
        addReversibleAction
    } = useGlobalStorage();

    const { isHidden, handleKeyEvent } = useHideAnnotations();
    const { settingsStore } = useSettings();
    const {
        annotationId,
        annotationIndex,
        dataset,
        image
    }: {
        dataset: Dataset;
        image: ImageSample;
        annotationId: string;
        annotationIndex?: number;
    } = $props();
    const keyToggleSelection = ' '; // spacebar
    const keyGoBack = get(settingsStore).key_go_back;
    let isPanModeEnabled = $state(false);

    const handleEscape = () => {
        if (image?.sample.dataset_id) {
            goto(routeHelpers.toAnnotations(image.sample.dataset_id));
        } else {
            goto('/');
        }
    };

    const handleKeyDownEvent = (event: KeyboardEvent) => {
        switch (event.key) {
            // Check for escape key
            case keyGoBack:
                handleEscape();
                break;
            // Add spacebar handling for selection toggle
            case ' ': // Space key
                event.preventDefault();
                if ($isEditingMode) {
                    isPanModeEnabled = true;
                } else {
                    toggleSampleAnnotationCropSelection(annotationId);
                }
                break;
            case keyToggleSelection:
                // Prevent default space behavior (like page scrolling)
                event.preventDefault();

                // Toggle selection based on context
                toggleSampleAnnotationCropSelection(annotationId);
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

    const datasetId = page.data.datasetId;
    const { rootDataset, refetch: refetchRootDataset } = useRootDatasetOptions({ datasetId });
    const { annotation: annotationResp, updateAnnotation } = $derived(
        useAnnotation({
            datasetId,
            annotationId
        })
    );

    beforeNavigate(() => {
        clearReversibleActions();
    });

    // Save when drag ends
    const onBoundingBoxChanged = (newBbox: BoundingBox) => {
        if (annotation) {
            const updatedAnnotation = {
                annotation_id: annotation.sample_id,
                dataset_id: datasetId,
                bounding_box: newBbox
            };

            const update = async () => {
                try {
                    await updateAnnotation(updatedAnnotation);
                    addAnnotationUpdateToUndoStack({
                        annotation,
                        dataset_id: datasetId,
                        addReversibleAction,
                        updateAnnotation
                    });
                } catch (error) {
                    toast.error('Failed to update annotations:' + (error as Error).message);
                }
            };
            update();
        }
    };

    let annotation = $derived($annotationResp.data);

    let sampleURL = $derived(getImageURL(annotation?.parent_sample_id || ''));

    let boundingBox = $derived(annotation ? getBoundingBox(annotation) : undefined);
    const { isEditingMode } = page.data.globalStorage;

    const cursor = $derived.by(() => {
        if (isPanModeEnabled) {
            return 'grab';
        }
        return 'auto';
    });
    const isResizable = $derived($isEditingMode && !isPanModeEnabled);
    let centeringBox = $state<BoundingBox | undefined>();

    // Recenter the zoomable container only on initial load of a new annotation
    $effect(() => {
        if (!centeringBox && boundingBox) {
            centeringBox = boundingBox;
        }
    });

    afterNavigate(() => {
        centeringBox = undefined;
    });

    const { imageBrightness, imageContrast } = useGlobalStorage();
</script>

<div class="flex h-full w-full flex-col space-y-4">
    <div class="flex w-full items-center justify-between">
        {#if $rootDataset.data}
            <AnnotationDetailsBreadcrumb rootDataset={$rootDataset.data} {annotationIndex} />
        {/if}
        {#if $isEditingMode}
            <ImageAdjustments bind:brightness={$imageBrightness} bind:contrast={$imageContrast} />
        {/if}
    </div>
    <Separator class="bg-border-hard" />
    <div class="flex min-h-0 flex-1 gap-4">
        <div class="flex-1">
            <Card className="h-full">
                <CardContent className="h-full">
                    {#if annotation}
                        <div class="h-full w-full overflow-hidden">
                            <div class="sample relative h-full w-full">
                                <div class="absolute right-4 top-2 z-30">
                                    <SelectableBox
                                        onSelect={() =>
                                            toggleSampleAnnotationCropSelection(annotationId)}
                                        isSelected={$selectedSampleAnnotationCropIds.has(
                                            annotationId
                                        )}
                                    />
                                </div>

                                <AnnotationDetailsNavigation />

                                <ZoomableContainer
                                    width={image.width}
                                    height={image.height}
                                    {cursor}
                                    boundingBox={centeringBox}
                                >
                                    {#snippet zoomableContent({ scale })}
                                        <image
                                            href={sampleURL}
                                            style={`filter: brightness(${$imageBrightness}) contrast(${$imageContrast})`}
                                        />
                                        <g class:invisible={$isHidden}>
                                            {#key $annotationResp.dataUpdatedAt}
                                                <SampleAnnotation
                                                    {annotation}
                                                    showLabel={true}
                                                    {scale}
                                                    imageWidth={image.width}
                                                    {isResizable}
                                                    {onBoundingBoxChanged}
                                                    constraintBox={{
                                                        x: 0,
                                                        y: 0,
                                                        width: image.width,
                                                        height: image.height
                                                    }}
                                                />
                                            {/key}
                                        </g>
                                    {/snippet}
                                </ZoomableContainer>
                            </div>
                        </div>
                    {:else}
                        <div class="flex h-full w-full items-center justify-center">
                            <Spinner size="large" align="center" />
                        </div>
                    {/if}
                </CardContent>
            </Card>
        </div>
        <div class="relative w-[375px]">
            <AnnotationDetailsPanel {annotationId} {image} />
        </div>
    </div>
</div>

<svelte:window onkeydown={handleKeyDownEvent} onkeyup={handleKeyUpEvent} />
