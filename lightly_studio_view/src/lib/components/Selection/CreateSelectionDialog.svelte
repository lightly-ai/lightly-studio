<script lang="ts">
    import { page } from '$app/state';
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { useSelectionDialog } from '$lib/hooks/useSelectionDialog/useSelectionDialog';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useCreateSelection } from '$lib/hooks/useCreateSelection';
    import type { SelectionRequest } from '$lib/api/lightly_studio_local/types.gen';
    import { type BalancingMode } from '$lib/components/Selection/balancingMode';
    import StrategySelect from '$lib/components/Selection/StrategySelect/StrategySelect.svelte';
    import ClassBalancingForm from '$lib/components/Selection/ClassBalancingForm/ClassBalancingForm.svelte';
    import SimilarityForm from '$lib/components/Selection/SimilarityForm/SimilarityForm.svelte';

    // Get collection ID from URL params
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

    // Form state
    let selectionStrategy = $state<
        'diversity' | 'typicality' | 'similarity' | 'class_balancing' | ''
    >('');
    let balancingMode = $state<BalancingMode>('uniform');
    let nSamplesToSelect = $state<number>(10);
    let queryTagId = $state('');
    let selectionResultTagName = $state<string>('');

    // Form validation
    const isFormValid = $derived(
        selectionStrategy !== '' &&
            (selectionStrategy === 'similarity' ? queryTagId !== '' : true) &&
            nSamplesToSelect > 0 &&
            selectionResultTagName.trim().length > 0
    );

    const isSimilaritySupported = $derived(!isVideoCollection);

    const noSamples = $derived($filteredSampleCount === 0);

    const notEnoughSamples = $derived(
        $filteredSampleCount > 0 && nSamplesToSelect > $filteredSampleCount
    );

    const selectionDescription = $derived(
        $filteredSampleCount > 0
            ? `Create a subset of the ${$filteredSampleCount} samples fulfilling the current filters.`
            : 'Create a subset of the samples fulfilling the current filters.'
    );

    const { isSubmitting, loadingMessage, submit } = useCreateSelection({
        get tags() {
            return tags;
        },
        get setTagSelected() {
            return setTagSelected;
        },
        get loadTags() {
            return loadTags;
        },
        closeSelectionDialog
    });

    async function handleFormSubmit(event: Event) {
        event.preventDefault();
        if (!isFormValid || notEnoughSamples || noSamples) return;

        const success = await submit({
            collectionId,
            isSimilaritySupported,
            selectionStrategy: selectionStrategy as
                | 'diversity'
                | 'typicality'
                | 'similarity'
                | 'class_balancing',
            nSamplesToSelect,
            selectionResultTagName,
            queryTagId,
            balancingMode,
            selectionFilter
        });

        if (success) resetForm();
    }

    function resetForm() {
        selectionStrategy = '';
        nSamplesToSelect = 10;
        queryTagId = '';
        selectionResultTagName = '';
    }
</script>

<Dialog.Root
    open={$isSelectionDialogOpen}
    onOpenChange={(open) => (open ? openSelectionDialog() : closeSelectionDialog())}
>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[425px]">
            <form onsubmit={handleFormSubmit}>
                <Dialog.Header>
                    <Dialog.Title class="text-foreground">Create Selection</Dialog.Title>
                    <Dialog.Description class="text-foreground">
                        {selectionDescription}
                    </Dialog.Description>
                </Dialog.Header>

                <div class="grid gap-4 py-4">
                    <!-- Strategy Selection -->
                    <StrategySelect
                        value={selectionStrategy}
                        {isSimilaritySupported}
                        onValueChange={(v) => (selectionStrategy = v)}
                    />

                    {#if selectionStrategy === 'class_balancing'}
                        <ClassBalancingForm
                            {balancingMode}
                            onBalancingModeChange={(mode) => (balancingMode = mode)}
                        />
                    {/if}

                    {#if selectionStrategy === 'similarity'}
                        <SimilarityForm
                            {queryTagId}
                            tags={$tags}
                            onQueryTagChange={(tagId) => (queryTagId = tagId)}
                        />
                    {/if}

                    <!-- Number of Samples Input -->
                    <div class="grid grid-cols-4 items-center gap-4">
                        <Label for="n-samples" class="text-right text-foreground">
                            Number of Samples
                        </Label>
                        <Input
                            id="n-samples"
                            type="number"
                            bind:value={nSamplesToSelect}
                            min="1"
                            class="col-span-3"
                            placeholder="Enter number of samples"
                            required
                            data-testid="selection-dialog-n-samples-input"
                        />
                    </div>

                    <!-- Tag Name Input -->
                    <div class="grid grid-cols-4 items-center gap-4">
                        <Label for="tag-name" class="text-right text-foreground">Tag Name</Label>
                        <Input
                            id="tag-name"
                            type="text"
                            bind:value={selectionResultTagName}
                            class="col-span-3"
                            placeholder="Enter a tag for the sampled subset"
                            required
                            data-testid="selection-dialog-tag-name-input"
                        />
                    </div>

                    <!-- Warning when no samples match the current filters -->
                    {#if noSamples}
                        <p
                            class="text-sm text-destructive"
                            data-testid="selection-dialog-no-samples-warning"
                        >
                            No samples match the current filters.
                        </p>
                    {/if}

                    <!-- Warning when requesting more samples than available -->
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

                <Dialog.Footer>
                    <Button
                        variant="outline"
                        type="button"
                        onclick={closeSelectionDialog}
                        disabled={$isSubmitting}
                        data-testid="selection-dialog-cancel"
                    >
                        Cancel
                    </Button>
                    <Button
                        type="submit"
                        disabled={!isFormValid || $isSubmitting || notEnoughSamples || noSamples}
                        data-testid="selection-dialog-submit"
                    >
                        {$isSubmitting ? $loadingMessage || 'Creating...' : 'Create Selection'}
                    </Button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
