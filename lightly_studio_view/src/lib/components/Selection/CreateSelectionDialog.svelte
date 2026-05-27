<script lang="ts">
    import { page } from '$app/state';
    import {
        createCombinationSelection,
        computeSimilarityMetadata,
        computeTypicalityMetadata
    } from '$lib/api/lightly_studio_local/sdk.gen';
    import type { SelectionRequest } from '$lib/api/lightly_studio_local/types.gen';
    import { Info } from '@lucide/svelte';
    import AddStrategyButton from '$lib/components/Selection/AddStrategyButton/AddStrategyButton.svelte';
    import FieldTooltip from '$lib/components/Selection/FieldTooltip.svelte';
    import StrategyCard from '$lib/components/Selection/StrategyCard/StrategyCard.svelte';
    import {
        isStrategyInstanceValid,
        type StrategyInstance
    } from '$lib/components/Selection/useStrategyBuilder/useStrategyBuilder';
    import { useStrategyBuilder } from '$lib/components/Selection/useStrategyBuilder/useStrategyBuilder';
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useSelectionDialog } from '$lib/hooks/useSelectionDialog/useSelectionDialog';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { toast } from 'svelte-sonner';

    const collectionId = $derived(page.params.collection_id!);

    const { loadTags, tags, setTagSelected } = $derived(
        useTags({ collection_id: collectionId, kind: ['sample'] })
    );

    const { isSelectionDialogOpen, openSelectionDialog, closeSelectionDialog } =
        useSelectionDialog();

    const isVideoCollection = $derived(
        page.data.collection?.sample_type === 'video' ||
            page.data.collection?.sample_type === 'video_frame'
    );

    const { imageFilter } = useImageFilters();
    const { videoFilter } = useVideoFilters();
    const { filteredSampleCount } = useGlobalStorage();
    const { metadataInfo } = $derived(useMetadataFilters(collectionId));
    const hasMetadataFields = $derived($metadataInfo.length > 0);

    const annotationLabelsQuery = $derived(
        useAnnotationLabels(() => ({ collectionId }))
    );
    const annotationLabels = $derived(
        (annotationLabelsQuery.data ?? []).map((label) => label.annotation_label_name)
    );
    const hasAnnotationLabels = $derived(annotationLabels.length > 0);

    const currentFilter = $derived(isVideoCollection ? $videoFilter : $imageFilter);
    const selectionFilter = $derived<SelectionRequest['filter']>(
        isVideoCollection
            ? currentFilter
                ? {
                      ...currentFilter,
                      filter_type: 'video'
                  }
                : null
            : currentFilter
              ? {
                    ...currentFilter,
                    filter_type: 'image'
                }
              : null
    );

    const {
        instances,
        addStrategy,
        duplicateStrategy,
        removeStrategy,
        resetStrategies,
        toggleExpand,
        updateParams
    } = useStrategyBuilder();

    let nSamplesToSelect = $state<number>(10);
    let selectionResultTagName = $state('');
    let isSubmitting = $state(false);
    let loadingMessage = $state('');

    const isFormValid = $derived(
        $instances.length > 0 &&
            $instances.every((instance) => isStrategyInstanceValid(instance)) &&
            nSamplesToSelect > 0 &&
            selectionResultTagName.trim().length > 0
    );

    const noSamples = $derived($filteredSampleCount === 0);
    const notEnoughSamples = $derived(
        $filteredSampleCount > 0 && nSamplesToSelect > $filteredSampleCount
    );

    const selectionDescription = $derived(
        $filteredSampleCount > 0
            ? `Create a subset of the ${$filteredSampleCount} samples fulfilling the current filters.`
            : 'Create a subset of the samples fulfilling the current filters.'
    );

    type SelectionError = {
        error?: string;
    };

    function handleFormSubmit(event: Event) {
        event.preventDefault();
        if (!isFormValid || notEnoughSamples || noSamples) {
            return;
        }

        void submitSelection();
    }

    function resetForm() {
        resetStrategies();
        nSamplesToSelect = 10;
        selectionResultTagName = '';
    }

    async function handleSelectionSuccess() {
        const createdTagName = selectionResultTagName;
        toast.success('Selection created successfully');
        await loadTags();

        const newTag = $tags.find((tag) => tag.name === createdTagName);
        if (newTag) {
            setTagSelected(newTag.tag_id, true);
        }

        closeSelectionDialog();
        resetForm();
    }

    function getMetadataKey(instance: StrategyInstance): string {
        if (instance.type === 'typicality') {
            return `typicality-${instance.id}`;
        }

        if (instance.type === 'similarity') {
            return `similarity-${instance.id}`;
        }

        if (instance.type === 'metadata_weighting') {
            return instance.params.metadata_key;
        }

        return '';
    }

    async function computeStrategyMetadata(instance: StrategyInstance): Promise<boolean> {
        if (instance.type === 'typicality') {
            loadingMessage = 'Computing typicality metadata...';
            const response = await computeTypicalityMetadata({
                path: { collection_id: collectionId },
                body: {
                    embedding_model_name: null,
                    metadata_name: getMetadataKey(instance)
                }
            });

            if (response.error) {
                toast.error(
                    'Failed to compute typicality metadata: ' +
                        ((response.error as SelectionError).error ?? 'Unknown error')
                );
                return false;
            }
        }

        if (instance.type === 'similarity') {
            if (isVideoCollection) {
                toast.error('Similarity is only available for image collections.');
                return false;
            }

            loadingMessage = 'Computing similarity metadata...';
            const response = await computeSimilarityMetadata({
                path: {
                    collection_id: collectionId,
                    query_tag_id: instance.params.query_tag_id
                },
                body: {
                    embedding_model_name: instance.params.embedding_model_name || null,
                    metadata_name: getMetadataKey(instance)
                }
            });

            if (response.error) {
                toast.error(
                    'Failed to compute similarity metadata: ' +
                        ((response.error as SelectionError).error ?? 'Unknown error')
                );
                return false;
            }
        }

        return true;
    }

    function toApiStrategy(instance: StrategyInstance): SelectionRequest['strategies'][number] {
        if (instance.type === 'diversity') {
            return {
                strategy_name: 'diversity',
                embedding_model_name: instance.params.embedding_model_name || null,
                strength: instance.params.strength
            };
        }

        if (instance.type === 'typicality' || instance.type === 'similarity') {
            return {
                strategy_name: 'weights',
                metadata_key: getMetadataKey(instance),
                strength: instance.params.strength
            };
        }

        if (instance.type === 'metadata_weighting') {
            return {
                strategy_name: 'weights',
                metadata_key: instance.params.metadata_key,
                strength: instance.params.strength
            };
        }

        return {
            strategy_name: 'balance',
            target_distribution: Object.fromEntries(
                instance.params.target_distribution.map((row) => [row.class_name, row.weight])
            ),
            strength: instance.params.strength
        };
    }

    async function performSelection(strategies: SelectionRequest['strategies']) {
        loadingMessage = 'Creating selection...';

        const response = await createCombinationSelection({
            path: { collection_id: collectionId },
            body: {
                n_samples_to_select: nSamplesToSelect,
                selection_result_tag_name: selectionResultTagName,
                strategies,
                filter: selectionFilter ?? undefined
            }
        });

        if (response.error) {
            toast.error((response.error as SelectionError).error ?? 'Failed to create selection');
            return false;
        }

        await handleSelectionSuccess();
        return true;
    }

    async function submitSelection() {
        isSubmitting = true;

        try {
            for (const instance of $instances) {
                const isSuccessful = await computeStrategyMetadata(instance);
                if (!isSuccessful) {
                    return;
                }
            }

            await performSelection($instances.map((instance) => toApiStrategy(instance)));
        } catch (error) {
            toast.error('Failed to create selection: ' + (error as Error).message);
        } finally {
            isSubmitting = false;
            loadingMessage = '';
        }
    }
</script>

<Dialog.Root
    open={$isSelectionDialogOpen}
    onOpenChange={(open) => (open ? openSelectionDialog() : closeSelectionDialog())}
>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[560px]">
            <form onsubmit={handleFormSubmit}>
                <Dialog.Header>
                    <Dialog.Title class="text-foreground">Create Selection</Dialog.Title>
                    <Dialog.Description class="text-foreground">
                        {selectionDescription}
                    </Dialog.Description>
                </Dialog.Header>

                <div class="max-h-[60vh] overflow-y-auto dark:[color-scheme:dark]">
                <div class="grid gap-4 py-4">
                    <div class="w-full">
                        <AddStrategyButton
                            similarityDisabledReason={isVideoCollection
                                ? 'Not available for video collections. Similarity selection requires image embeddings.'
                                : $tags.length === 0
                                  ? 'No sample tags in this collection. Create a sample tag first to use as the similarity reference.'
                                  : undefined}
                            metadataWeightingDisabledReason={!hasMetadataFields
                                ? 'No numeric metadata fields found. Index metadata on your samples to enable this strategy.'
                                : undefined}
                            classBalancingDisabledReason={!hasAnnotationLabels
                                ? 'No annotation labels found. Add annotations to your samples to enable this strategy.'
                                : undefined}
                            onAdd={addStrategy}
                        />
                    </div>

                    {#if $instances.length > 0}
                    <div class="grid gap-3">
                        <Label class="text-foreground">Strategies</Label>
                        {#each $instances as instance (instance.id)}
                            <StrategyCard
                                {instance}
                                tags={$tags}
                                {annotationLabels}
                                onRemove={() => removeStrategy(instance.id)}
                                onDuplicate={() => duplicateStrategy(instance.id)}
                                onUpdate={(params) => updateParams(instance.id, params)}
                                onToggleExpand={() => toggleExpand(instance.id)}
                            />
                        {/each}
                        <span class="flex items-center gap-1 text-xs text-muted-foreground">
                            <Info class="size-3 shrink-0" />
                            Strategies are scored and combined simultaneously using their strength weights — the order shown here does not affect the result.
                        </span>
                    </div>
                    {/if}

                    <div class="grid gap-2">
                        <div class="flex items-center gap-1.5">
                            <Label for="n-samples" class="text-foreground">Number of Samples</Label>
                            <FieldTooltip content="How many samples will be written to the output tag. Cannot exceed the number of samples matching the current filters." />
                        </div>
                        <Input
                            id="n-samples"
                            type="number"
                            bind:value={nSamplesToSelect}
                            min="1"
                            placeholder="Enter number of samples"
                            required
                            data-testid="selection-dialog-n-samples-input"
                        />
                    </div>

                    <div class="grid gap-2">
                        <div class="flex items-center gap-1.5">
                            <Label for="tag-name" class="text-foreground">Tag Name</Label>
                            <FieldTooltip content="A new sample tag will be created with this name to store the selection result." />
                        </div>
                        <Input
                            id="tag-name"
                            type="text"
                            bind:value={selectionResultTagName}
                            placeholder="Enter a tag for the sampled subset"
                            required
                            data-testid="selection-dialog-tag-name-input"
                        />
                    </div>

                    {#if noSamples}
                        <p
                            class="text-sm text-destructive"
                            data-testid="selection-dialog-no-samples-warning"
                        >
                            No samples match the current filters.
                        </p>
                    {/if}

                    {#if notEnoughSamples}
                        <p
                            class="text-sm text-destructive"
                            data-testid="selection-dialog-not-enough-samples-warning"
                        >
                            Only {$filteredSampleCount} samples are available, but {nSamplesToSelect}
                            were requested.
                        </p>
                    {/if}
                </div>
                </div>

                <Dialog.Footer class="mt-4">
                    <a
                        href="#"
                        class="mr-auto self-center text-xs text-muted-foreground underline-offset-4 hover:underline"
                        data-testid="selection-dialog-docs-link"
                    >
                        Learn more about combination selection →
                    </a>
                    <Button
                        variant="outline"
                        type="button"
                        onclick={closeSelectionDialog}
                        disabled={isSubmitting}
                        data-testid="selection-dialog-cancel"
                    >
                        Cancel
                    </Button>
                    <Button
                        type="submit"
                        disabled={!isFormValid || isSubmitting || notEnoughSamples || noSamples}
                        data-testid="selection-dialog-submit"
                    >
                        {isSubmitting ? loadingMessage || 'Creating...' : 'Create Selection'}
                    </Button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
