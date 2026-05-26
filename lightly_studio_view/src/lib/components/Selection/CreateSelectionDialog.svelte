<script lang="ts">
    import { page } from '$app/state';
    import {
        createCombinationSelection,
        computeSimilarityMetadata,
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
    import { BALANCING_MODE_LABELS, type BalancingMode } from './balancingMode';

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
        'diversity' | 'typicality' | 'similarity' | 'class_distribution' | ''
    >('');
    let balancingMode = $state<BalancingMode>('uniform');
    let nSamplesToSelect = $state<number>(10);
    let queryTagId = $state('');
    let selectionResultTagName = $state<string>('');
    let isSubmitting = $state(false);
    let loadingMessage = $state<string>('');

    const STRATEGY_LABELS: Record<string, string> = {
        diversity: 'Diversity',
        typicality: 'Typicality',
        similarity: 'Similarity',
        class_distribution: 'Class Balancing'
    };

    // Form validation
    const isFormValid = $derived(
        selectionStrategy !== '' &&
            (selectionStrategy === 'similarity' ? queryTagId !== '' : true) &&
            nSamplesToSelect > 0 &&
            selectionResultTagName.trim().length > 0
    );

    const isSimilaritySupported = $derived(!isVideoCollection);
    const selectedQueryTagName = $derived(
        $tags.find((tag) => tag.tag_id === queryTagId)?.name ?? 'Select tag'
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

    function handleFormSubmit(event: Event) {
        event.preventDefault();
        if (!isFormValid || notEnoughSamples || noSamples) return;

        submitSelection();
    }

    function resetForm() {
        selectionStrategy = '';
        nSamplesToSelect = 10;
        queryTagId = '';
        selectionResultTagName = '';
    }

    async function handleSelectionSuccess() {
        const createdTagName = selectionResultTagName;
        toast.success('Selection created successfully');
        await loadTags();

        // Select the newly created tag
        const newTag = $tags.find((tag) => tag.name === createdTagName);
        if (newTag) {
            setTagSelected(newTag.tag_id, true);
        }

        closeSelectionDialog();
        resetForm();
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
            toast.error(
                (response.error as { error?: string }).error || 'Failed to create selection'
            );
            return false;
        }

        await handleSelectionSuccess();
        return true;
    }

    async function submitSelection() {
        isSubmitting = true;

        type SelectionError = {
            error: string;
        };

        try {
            if (selectionStrategy === 'diversity') {
                await performSelection([
                    {
                        strategy_name: 'diversity',
                        embedding_model_name: null
                    }
                ]);
            } else if (selectionStrategy === 'class_distribution') {
                await performSelection([
                    {
                        strategy_name: 'balance',
                        target_distribution: balancingMode
                    }
                ]);
            } else if (selectionStrategy === 'typicality') {
                loadingMessage = 'Computing typicality metadata...';
                const typicalityResponse = await computeTypicalityMetadata({
                    path: { collection_id: collectionId },
                    body: {
                        embedding_model_name: null,
                        metadata_name: 'typicality'
                    }
                });

                if (typicalityResponse.error) {
                    toast.error(
                        'Failed to compute typicality metadata: ' +
                            ((typicalityResponse.error as SelectionError).error || 'Unknown error')
                    );
                    return;
                }

                await performSelection([
                    {
                        strategy_name: 'weights',
                        metadata_key: 'typicality'
                    }
                ]);
            } else if (selectionStrategy === 'similarity') {
                if (!isSimilaritySupported) {
                    toast.error('Similarity is only available for image collections.');
                    return;
                }

                loadingMessage = 'Computing similarity metadata...';
                const response = await computeSimilarityMetadata({
                    path: { collection_id: collectionId, query_tag_id: queryTagId },
                    body: {
                        embedding_model_name: null,
                        metadata_name: 'similarity'
                    }
                });

                if (response.error) {
                    toast.error(
                        'Failed to compute similarity metadata: ' +
                            ((response.error as SelectionError).error || 'Unknown error')
                    );
                    return;
                }

                await performSelection([
                    {
                        strategy_name: 'weights',
                        metadata_key: 'similarity'
                    }
                ]);
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
                                {STRATEGY_LABELS[selectionStrategy] ?? 'Select strategy'}
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
                                    <Select.Item
                                        value="class_distribution"
                                        label="Class Balancing"
                                        data-testid="selection-strategy-class-distribution"
                                        >Class Balancing</Select.Item
                                    >
                                    <Select.Item
                                        value="similarity"
                                        label="Similarity"
                                        data-testid="selection-strategy-similarity"
                                        disabled={!isSimilaritySupported}>Similarity</Select.Item
                                    >
                                </Select.Group>
                            </Select.Content>
                        </Select.Root>
                    </div>

                    {#if selectionStrategy === 'class_distribution'}
                        <div class="grid grid-cols-4 items-center gap-4">
                            <Label for="balancing-mode" class="text-right text-foreground">
                                Balancing Mode
                            </Label>
                            <Select.Root
                                type="single"
                                name="balancing-mode"
                                bind:value={balancingMode}
                            >
                                <Select.Trigger
                                    class="col-span-3"
                                    data-testid="selection-dialog-balancing-mode-select"
                                >
                                    {BALANCING_MODE_LABELS[balancingMode]}
                                </Select.Trigger>
                                <Select.Content>
                                    <Select.Group>
                                        <Select.Item
                                            value="uniform"
                                            label="Uniform"
                                            data-testid="selection-balancing-mode-uniform"
                                            >Uniform</Select.Item
                                        >
                                        <Select.Item value="dictionary" label="Dictionary" disabled
                                            >Dictionary (Coming soon)</Select.Item
                                        >
                                        <Select.Item
                                            value="input"
                                            label="Input"
                                            data-testid="selection-balancing-mode-input"
                                            disabled>Input (Coming soon)</Select.Item
                                        >
                                    </Select.Group>
                                </Select.Content>
                            </Select.Root>
                        </div>
                    {/if}

                    {#if selectionStrategy === 'similarity'}
                        <div class="grid grid-cols-4 items-center gap-4">
                            <Label for="query-tag" class="text-right text-foreground">
                                Query Tag
                            </Label>
                            <Select.Root type="single" name="query-tag" bind:value={queryTagId}>
                                <Select.Trigger
                                    class="col-span-3"
                                    data-testid="selection-dialog-query-tag-select"
                                >
                                    {selectedQueryTagName}
                                </Select.Trigger>
                                <Select.Content>
                                    <Select.Group>
                                        {#if $tags.length === 0}
                                            <div
                                                class="py-1.5 pl-8 pr-2 text-sm italic text-muted-foreground"
                                                data-testid="selection-dialog-no-query-tags"
                                            >
                                                No sample tags available.
                                            </div>
                                        {:else}
                                            {#each $tags as tag (tag.tag_id)}
                                                <Select.Item
                                                    value={tag.tag_id}
                                                    label={tag.name}
                                                    data-testid={`selection-query-tag-${tag.tag_id}`}
                                                >
                                                    {tag.name}
                                                </Select.Item>
                                            {/each}
                                        {/if}
                                    </Select.Group>
                                </Select.Content>
                            </Select.Root>
                        </div>
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
