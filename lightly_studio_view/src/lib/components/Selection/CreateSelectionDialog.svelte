<script lang="ts">
    import { page } from '$app/state';
    import {
        createCombinationSelection,
        computeTypicalityMetadata
    } from '$lib/api/lightly_studio_local/sdk.gen';
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import * as Select from '$lib/components/ui/select';
    import { toast } from 'svelte-sonner';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { useSelectionDialog } from '$lib/hooks/useSelectionDialog/useSelectionDialog';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { SelectionRequest } from '$lib/api/lightly_studio_local/types.gen';

    // Get collection ID from URL params
    const collectionId = $derived(page.params.collection_id!);

    const { loadTags } = $derived(useTags({ collection_id: collectionId, kind: ['sample'] }));

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
    let selectionStrategy = $state<'diversity' | 'typicality' | ''>('');
    let nSamplesToSelect = $state<number>(10);
    let selectionResultTagName = $state<string>('');
    let isSubmitting = $state(false);
    let loadingMessage = $state<string>('');

    // Form validation
    const isFormValid = $derived(
        selectionStrategy !== '' && nSamplesToSelect > 0 && selectionResultTagName.trim().length > 0
    );

    const notEnoughSamples = $derived(
        $filteredSampleCount > 0 && nSamplesToSelect > $filteredSampleCount
    );

    const selectionDescription = $derived(
        $filteredSampleCount > 0
            ? `Create a subset of the ${$filteredSampleCount} samples fulfilling the current filters.`
            : 'Create a subset of the samples fulfilling the current filters.'
    );

    function handleFormSubmit(event: Event) {
        event.preventDefault();
        if (!isFormValid || notEnoughSamples) return;

        submitSelection();
    }

    function handleSelectionSuccess() {
        toast.success('Selection created successfully');
        loadTags();

        closeSelectionDialog();

        selectionStrategy = '';
        nSamplesToSelect = 10;
        selectionResultTagName = '';
    }

    async function submitSelection() {
        isSubmitting = true;

        type SelectionError = {
            error: string;
        };

        let responseError: SelectionError | null = null;

        try {
            if (selectionStrategy === 'diversity') {
                const response = await createCombinationSelection({
                    path: { collection_id: collectionId },
                    body: {
                        n_samples_to_select: nSamplesToSelect,
                        selection_result_tag_name: selectionResultTagName,
                        strategies: [
                            {
                                strategy_name: 'diversity',
                                embedding_model_name: null
                            }
                        ],
                        filter: selectionFilter ?? undefined
                    }
                });

                responseError = response.error as SelectionError;
                if (responseError) {
                    toast.error(String(responseError.error) || 'Failed to create selection');
                    return;
                }

                handleSelectionSuccess();
            } else if (selectionStrategy === 'typicality') {
                // First, compute typicality metadata.
                loadingMessage = 'Computing typicality metadata...';
                const typicalityResponse = await computeTypicalityMetadata({
                    path: { collection_id: collectionId },
                    body: {
                        embedding_model_name: null,
                        metadata_name: 'typicality'
                    }
                });

                responseError = typicalityResponse.error as SelectionError;
                if (typicalityResponse.error) {
                    toast.error(
                        'Failed to compute typicality metadata: ' +
                            (responseError.error || 'Unknown error')
                    );
                    return;
                }

                // Then create selection with weighting strategy.
                loadingMessage = 'Creating selection...';
                const selectionResponse = await createCombinationSelection({
                    path: { collection_id: collectionId },
                    body: {
                        n_samples_to_select: nSamplesToSelect,
                        selection_result_tag_name: selectionResultTagName,
                        strategies: [
                            {
                                strategy_name: 'weights',
                                metadata_key: 'typicality'
                            }
                        ],
                        filter: selectionFilter ?? undefined
                    }
                });

                responseError = selectionResponse.error as SelectionError;
                if (responseError) {
                    toast.error(responseError.error || 'Failed to create selection');
                    return;
                }

                handleSelectionSuccess();
            }
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
                    <div class="grid grid-cols-4 items-center gap-4">
                        <Label for="strategy" class="text-right text-foreground">Strategy</Label>
                        <Select.Root type="single" name="strategy" bind:value={selectionStrategy}>
                            <Select.Trigger
                                class="col-span-3"
                                data-testid="selection-dialog-strategy-select"
                            >
                                {selectionStrategy === 'diversity'
                                    ? 'Diversity'
                                    : selectionStrategy === 'typicality'
                                      ? 'Typicality'
                                      : 'Select strategy'}
                            </Select.Trigger>
                            <Select.Content>
                                <Select.Group>
                                    <Select.Item
                                        value="diversity"
                                        label="Diversity"
                                        data-testid="selection-strategy-diversity"
                                        >Diversity</Select.Item
                                    >
                                    <Select.Item
                                        value="typicality"
                                        label="Typicality"
                                        data-testid="selection-strategy-typicality"
                                        >Typicality</Select.Item
                                    >
                                </Select.Group>
                            </Select.Content>
                        </Select.Root>
                    </div>

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
                        disabled={isSubmitting}
                        data-testid="selection-dialog-cancel"
                    >
                        Cancel
                    </Button>
                    <Button
                        type="submit"
                        disabled={!isFormValid || isSubmitting || notEnoughSamples}
                        data-testid="selection-dialog-submit"
                    >
                        {isSubmitting ? loadingMessage || 'Creating...' : 'Create Selection'}
                    </Button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
