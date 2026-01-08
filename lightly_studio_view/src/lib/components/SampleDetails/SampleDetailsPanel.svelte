<script lang="ts">
    import { afterNavigate } from '$app/navigation';
    import { Card, CardContent, SampleDetailsSidePanel } from '$lib/components';
    import { ImageAdjustments } from '$lib/components/ImageAdjustments';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useSettings } from '$lib/hooks/useSettings';
    import { type Snippet } from 'svelte';
    import { toast } from 'svelte-sonner';

    import { get } from 'svelte/store';
    import { getAnnotations } from '../SampleAnnotation/utils';
    import Spinner from '../Spinner/Spinner.svelte';
    import {
        AnnotationType,
        type AnnotationView,
        type CaptionView,
        type CollectionViewWithCount,
        type TagView
    } from '$lib/api/lightly_studio_local';
    import { useRemoveTagFromSample } from '$lib/hooks/useRemoveTagFromSample/useRemoveTagFromSample';
    import { useRootCollectionOptions } from '$lib/hooks/useRootCollection/useRootCollection';
    import SampleDetailsToolbar from './SampleDetailsToolbar/SampleDetailsToolbar.svelte';
    import SampleDetailsSelectableBox from './SampleDetailsSelectableBox/SampleDetailsSelectableBox.svelte';
    import SampleDetailsImageContainer from './SampleDetailsImageContainer/SampleDetailsImageContainer.svelte';
    import {
        createAnnotationLabelContext,
        useAnnotationLabelContext
    } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { createSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';

    const {
        sampleId,
        collectionId,
        children,
        sampleURL,
        refetch,
        handleEscape,
        sample,
        metadataValue,
        breadcrumb
    }: {
        sampleId: string;
        collectionId: string;
        sampleURL: string;
        sample: {
            width: number;
            height: number;
            annotations: AnnotationView[];
            captions: CaptionView[] | undefined;
            tags: TagView[] | undefined;
            sample_id: string;
        };
        refetch: () => void;
        handleEscape: () => void;
        children: Snippet | undefined;
        metadataValue: Snippet;
        breadcrumb: Snippet<[{ collection: CollectionViewWithCount }]>;
    } = $props();

    const {
        toggleSampleSelection,
        clearReversibleActions,
        lastAnnotationType,
        lastAnnotationBrushSize,
        imageBrightness,
        imageContrast
    } = useGlobalStorage();

    const { handleKeyEvent } = useHideAnnotations();
    const { settingsStore } = useSettings();
    const { removeTagFromSample } = useRemoveTagFromSample({
        collectionId
    });
    const { isEditingMode } = useGlobalStorage();

    createAnnotationLabelContext({});
    createSampleDetailsToolbarContext();

    const annotationLabelContext = useAnnotationLabelContext();

    const addOrEditAnnotationIsEnabled = $derived(!!annotationLabelContext.annotationType);

    let isPanModeEnabled = $state(false);

    let annotationsIdsToHide = $state<Set<string>>(new Set());

    // Handle keyboard events
    const handleKeyDownEvent = (event: KeyboardEvent) => {
        switch (event.key) {
            // Check for escape key
            case get(settingsStore).key_go_back:
                if ($isEditingMode) {
                    if (annotationLabelContext.annotationType) {
                        annotationLabelContext.annotationLabel = undefined;
                        annotationLabelContext.annotationType = undefined;
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

    afterNavigate(() => {
        annotationLabelContext.annotationId = undefined;
        annotationLabelContext.isDrawing = false;
        annotationLabelContext.lastCreatedAnnotationId = undefined;
        clearReversibleActions();
    });

    const toggleAnnotationSelection = (annotationId: string) => {
        if (isPanModeEnabled) return;

        annotationLabelContext.annotationId =
            annotationLabelContext.annotationId === annotationId ? null : annotationId;
    };

    let annotationsToShow = $derived(sample?.annotations ? getAnnotations(sample.annotations) : []);

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

    const { rootCollection } = useRootCollectionOptions({
        collectionId
    });

    const isResizable = $derived($isEditingMode && !isPanModeEnabled);
    const isDrawingEnabled = $derived(!!annotationLabelContext.annotationType && !isPanModeEnabled);

    let htmlContainer: HTMLDivElement | null = $state(null);
    let annotationType = $derived<string>(
        annotationLabelContext.annotationType ??
            $lastAnnotationType[collectionId] ??
            AnnotationType.OBJECT_DETECTION
    );
    let isEraser = $state(false);
    let brushRadius = $state($lastAnnotationBrushSize[collectionId] ?? 2);

    $effect(() => {
        if (!$isEditingMode) {
            isEraser = false;
        }
    });
</script>

{#if sample}
    <div class="flex h-full w-full flex-col space-y-4">
        <div class="flex w-full items-center justify-between">
            {#if $rootCollection.data}
                {@render breadcrumb({ collection: $rootCollection.data })}
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
                                        ...sample,
                                        sampleId,
                                        annotations: annotationsToShow
                                    }}
                                    {collectionId}
                                    imageUrl={sampleURL}
                                    hideAnnotationsIds={annotationsIdsToHide}
                                    {isResizable}
                                    {isDrawingEnabled}
                                    {isEraser}
                                    addAnnotationEnabled={addOrEditAnnotationIsEnabled}
                                    selectedAnnotationId={annotationLabelContext.annotationId}
                                    draftAnnotationLabel={annotationLabelContext.annotationLabel}
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
                    bind:annotationsIdsToHide
                    sample={{
                        ...sample,
                        annotations: annotationsToShow
                    }}
                    onRemoveTag={handleRemoveTag}
                    onUpdate={refetch}
                    {collectionId}
                    {isPanModeEnabled}
                >
                    {#snippet metadataItem()}
                        {@render metadataValue()}
                    {/snippet}
                </SampleDetailsSidePanel>
            </div>
        </div>
    </div>
{:else}
    <div data-testid="sample-details-loading">
        <Spinner />
    </div>
{/if}

<svelte:window onkeydown={handleKeyDownEvent} onkeyup={handleKeyUpEvent} />
