<script lang="ts">
    import { afterNavigate, goto } from '$app/navigation';
    import { Card, CardContent, SampleDetailsSidePanel } from '$lib/components';
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

    import { get } from 'svelte/store';
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
    import type { ListItem } from '../SelectList/types';
    import { useDeleteCaption } from '$lib/hooks/useDeleteCaption/useDeleteCaption';
    import { useRemoveTagFromSample } from '$lib/hooks/useRemoveTagFromSample/useRemoveTagFromSample';
    import { page } from '$app/state';
    import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
    import { useRootCollectionOptions } from '$lib/hooks/useRootCollection/useRootCollection';
    import SampleDetailsToolbar from './SampleDetailsToolbar/SampleDetailsToolbar.svelte';
    import SampleDetailsSelectableBox from './SampleDetailsSelectableBox/SampleDetailsSelectableBox.svelte';
    import SampleDetailsImageContainer from './SampleDetailsImageContainer/SampleDetailsImageContainer.svelte';

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
        toggleSampleSelection,
        clearReversibleActions,
        lastAnnotationType,
        lastAnnotationBrushSize
    } = useGlobalStorage();
    const collectionId = collection.collection_id!;

    const { handleKeyEvent } = useHideAnnotations();
    const { settingsStore } = useSettings();
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

    afterNavigate(() => {
        selectedAnnotationId = undefined;
        addAnnotationEnabled = false;
        addAnnotationLabel = undefined;
        clearReversibleActions();
    });

    const toggleAnnotationSelection = (annotationId: string) => {
        if (isPanModeEnabled) return;

        if (selectedAnnotationId === annotationId) {
            selectedAnnotationId = undefined;
        } else {
            selectedAnnotationId = annotationId;
        }
    };

    let addAnnotationEnabled = $state(false);

    $effect(() => {
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

    const isResizable = $derived($isEditingMode && !isPanModeEnabled);
    const isDrawingEnabled = $derived(
        addAnnotationEnabled && !isPanModeEnabled && addAnnotationLabel !== undefined
    );

    let htmlContainer: HTMLDivElement | null = $state(null);
    let annotationType = $state<string | null>(
        $lastAnnotationType[collectionId] ?? AnnotationType.OBJECT_DETECTION
    );
    let isEraser = $state(false);
    let brushRadius = $state($lastAnnotationBrushSize[collectionId] ?? 2);

    $effect(() => {
        if (!$isEditingMode) {
            isEraser = false;
        }
    });
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
                                <SampleDetailsSelectableBox {sampleId} {collectionId} />

                                {#if children}
                                    {@render children()}
                                {/if}
                                <SampleDetailsImageContainer
                                    sample={{
                                        ...$image.data,
                                        annotations: annotationsToShow
                                    }}
                                    {collectionId}
                                    imageUrl={sampleURL}
                                    hideAnnotationsIds={annotationsIdsToHide}
                                    {isResizable}
                                    {isDrawingEnabled}
                                    {isEraser}
                                    {addAnnotationEnabled}
                                    {selectedAnnotationId}
                                    draftAnnotationLabel={addAnnotationLabel}
                                    {brushRadius}
                                    {refetch}
                                    {annotationType}
                                    {toggleAnnotationSelection}
                                />
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
            <div class="relative w-[375px]">
                <SampleDetailsSidePanel
                    bind:addAnnotationEnabled
                    bind:addAnnotationLabel
                    bind:annotationsIdsToHide
                    bind:annotationType
                    sample={$image.data}
                    {selectedAnnotationId}
                    onDeleteCaption={handleDeleteCaption}
                    {onCreateCaption}
                    onRemoveTag={handleRemoveTag}
                    onUpdate={refetch}
                    {collectionId}
                    {isPanModeEnabled}
                />
            </div>
        </div>
    </div>
{:else}
    <div data-testid="sample-details-loading">
        <Spinner />
    </div>
{/if}

<svelte:window onkeydown={handleKeyDownEvent} onkeyup={handleKeyUpEvent} />
