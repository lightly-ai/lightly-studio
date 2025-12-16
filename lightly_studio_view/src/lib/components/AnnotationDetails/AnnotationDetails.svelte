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
    import type { Dataset } from '$lib/services/types';
    import { page } from '$app/state';
    import { ZoomableContainer } from '$lib/components';
    import { getBoundingBox } from '../SampleAnnotation/utils';
    import Spinner from '../Spinner/Spinner.svelte';
    import type { BoundingBox } from '$lib/types';
    import { toast } from 'svelte-sonner';
    import { addAnnotationUpdateToUndoStack } from '$lib/services/addAnnotationUpdateToUndoStack';
    import {
        type AnnotationDetailsWithPayloadView,
        type AnnotationUpdateInput,
        type AnnotationView
    } from '$lib/api/lightly_studio_local';
    import type { Snippet } from 'svelte';

    type SampleProperties = {
        width: number;
        height: number;
        url: string;
    };
    const {
        toggleSampleAnnotationCropSelection,
        selectedSampleAnnotationCropIds,
        clearReversibleActions,
        addReversibleAction
    } = useGlobalStorage();

    const { isHidden, handleKeyEvent } = useHideAnnotations();
    const { settingsStore } = useSettings();
    const {
        annotationIndex,
        dataset,
        annotationDetails,
        parentSample,
        parentSampleDetails,
        updateAnnotation,
        refetch,
        datasetId
    }: {
        dataset: Dataset;
        annotationIndex?: number;
        annotationDetails: AnnotationDetailsWithPayloadView;
        parentSample: SampleProperties;
        parentSampleDetails: Snippet;
        updateAnnotation: (input: AnnotationUpdateInput) => Promise<void>;
        refetch: () => void;
        datasetId: string;
    } = $props();
    const keyToggleSelection = ' '; // spacebar
    const keyGoBack = get(settingsStore).key_go_back;
    let isPanModeEnabled = $state(false);

    const handleEscape = () => {
        if (annotationDetails.parent_sample_data?.sample.dataset_id) {
            goto(
                routeHelpers.toAnnotations(annotationDetails.parent_sample_data.sample.dataset_id)
            );
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
                    toggleSampleAnnotationCropSelection(datasetId, annotationId);
                }
                break;
            case keyToggleSelection:
                // Prevent default space behavior (like page scrolling)
                event.preventDefault();

                // Toggle selection based on context
                toggleSampleAnnotationCropSelection(datasetId, annotationId);
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

    let annotation: AnnotationView = $derived(annotationDetails.annotation);
    let annotationId = $derived(annotation.sample_id);

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
        <AnnotationDetailsBreadcrumb {dataset} {annotationIndex} />
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
                                            toggleSampleAnnotationCropSelection(
                                                datasetId,
                                                annotationId
                                            )}
                                        isSelected={$selectedSampleAnnotationCropIds[
                                            datasetId
                                        ]?.has(annotationId)}
                                    />
                                </div>

                                <AnnotationDetailsNavigation />

                                <ZoomableContainer
                                    width={parentSample.width}
                                    height={parentSample.height}
                                    {cursor}
                                    boundingBox={centeringBox}
                                >
                                    {#snippet zoomableContent({ scale })}
                                        <image
                                            href={parentSample.url}
                                            style={`filter: brightness(${$imageBrightness}) contrast(${$imageContrast})`}
                                        />
                                        <g class:invisible={$isHidden}>
                                            {#key annotation.sample_id}
                                                <SampleAnnotation
                                                    {annotation}
                                                    showLabel={true}
                                                    {scale}
                                                    imageWidth={parentSample.width}
                                                    {isResizable}
                                                    {onBoundingBoxChanged}
                                                    constraintBox={{
                                                        x: 0,
                                                        y: 0,
                                                        width: parentSample.width,
                                                        height: parentSample.height
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
            <AnnotationDetailsPanel {annotation} onUpdate={refetch}>
                {#snippet sampleDetails()}
                    {@render parentSampleDetails()}
                {/snippet}
            </AnnotationDetailsPanel>
        </div>
    </div>
</div>

<svelte:window onkeydown={handleKeyDownEvent} onkeyup={handleKeyUpEvent} />
