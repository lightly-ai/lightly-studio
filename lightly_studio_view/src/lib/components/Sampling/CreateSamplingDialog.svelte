<script lang="ts">
    import { page } from '$app/state';
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { useSamplingDialog } from '$lib/hooks/useSamplingDialog/useSamplingDialog';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useCreateSampling } from '$lib/hooks/useCreateSampling';
    import type { SamplingRequest } from '$lib/api/lightly_studio_local/types.gen';
    import { type BalancingMode } from '$lib/components/Sampling/balancingMode';
    import StrategySelect from '$lib/components/Sampling/StrategySelect/StrategySelect.svelte';
    import ClassBalancingForm from '$lib/components/Sampling/ClassBalancingForm/ClassBalancingForm.svelte';
    import SimilarityForm from '$lib/components/Sampling/SimilarityForm/SimilarityForm.svelte';

    // Get collection ID from URL params
    const collectionId = $derived(page.params.collection_id!);

    const { loadTags, tags, setTagSelected } = $derived(
        useTags({ collection_id: collectionId, kind: ['sample'] })
    );

    const { isSamplingDialogOpen, openSamplingDialog, closeSamplingDialog } = useSamplingDialog();
    const annotationCollectionsQuery = $derived(useAnnotationCollections({ collectionId }));

    const isVideoCollection = $derived(
        page.data.collection?.sample_type === 'video' ||
            page.data.collection?.sample_type === 'video_frame'
    );

    const { imageFilter } = useImageFilters();
    const { videoFilter } = useVideoFilters();
    const { filteredSampleCount } = useGlobalStorage();

    const currentFilter = $derived(isVideoCollection ? $videoFilter : $imageFilter);
    const annotationCollections = $derived(annotationCollectionsQuery.data ?? []);
    const samplingFilter = $derived<SamplingRequest['filter']>(
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
    let samplingStrategy = $state<
        'diversity' | 'typicality' | 'similarity' | 'class_balancing' | ''
    >('');
    let balancingMode = $state<BalancingMode>('uniform');
    let nSamplesToSelect = $state<number>(10);
    let queryTagId = $state('');
    let annotationSourceId = $state('');
    let classTargets = $state<Record<string, number>>({});
    let samplingResultTagName = $state<string>('');

    // Form validation
    const isFormValid = $derived(
        samplingStrategy !== '' &&
            (samplingStrategy === 'similarity' ? queryTagId !== '' : true) &&
            (samplingStrategy === 'class_balancing' && balancingMode === 'dictionary'
                ? Object.keys(classTargets).length > 0
                : true) &&
            nSamplesToSelect > 0 &&
            samplingResultTagName.trim().length > 0
    );

    const validationErrorMessage = $derived.by(() => {
        if (samplingStrategy === '') return 'Select a sampling strategy';
        if (samplingStrategy === 'similarity' && queryTagId === '') return 'Select a query tag';
        if (
            samplingStrategy === 'class_balancing' &&
            balancingMode === 'dictionary' &&
            Object.keys(classTargets).length === 0
        ) {
            return 'Add at least one class target';
        }
        if (nSamplesToSelect <= 0) return 'Number of samples must be greater than 0';
        if (samplingResultTagName.trim().length === 0) return 'Enter a tag name';
        return '';
    });

    const isSimilaritySupported = $derived(!isVideoCollection);

    const noSamples = $derived($filteredSampleCount === 0);

    const notEnoughSamples = $derived(
        $filteredSampleCount > 0 && nSamplesToSelect > $filteredSampleCount
    );

    const sampleCountLabel = $derived(
        `${$filteredSampleCount} ${$filteredSampleCount === 1 ? 'sample' : 'samples'}`
    );

    const { isSubmitting, loadingMessage, submit } = useCreateSampling({
        get tags() {
            return tags;
        },
        get setTagSelected() {
            return setTagSelected;
        },
        get loadTags() {
            return loadTags;
        },
        closeSamplingDialog
    });

    async function handleFormSubmit(event: Event) {
        event.preventDefault();
        if (!isFormValid || notEnoughSamples || noSamples) return;

        const success = await submit({
            collectionId,
            isSimilaritySupported,
            samplingStrategy: samplingStrategy as
                | 'diversity'
                | 'typicality'
                | 'similarity'
                | 'class_balancing',
            nSamplesToSelect,
            samplingResultTagName,
            queryTagId,
            balancingMode,
            annotationSourceId,
            classTargets,
            samplingFilter
        });

        if (success) resetForm();
    }

    function resetForm() {
        samplingStrategy = '';
        balancingMode = 'uniform';
        nSamplesToSelect = 10;
        queryTagId = '';
        annotationSourceId = '';
        classTargets = {};
        samplingResultTagName = '';
    }
</script>

<Dialog.Root
    open={$isSamplingDialogOpen}
    onOpenChange={(open) => (open ? openSamplingDialog() : closeSamplingDialog())}
>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[425px]">
            <form onsubmit={handleFormSubmit}>
                <Dialog.Header>
                    <Dialog.Title class="text-foreground">Create Sampling</Dialog.Title>
                    <Dialog.Description class="text-foreground">
                        Sample from the <strong class="font-semibold text-primary"
                            >{sampleCountLabel}</strong
                        > currently matching your filters.
                    </Dialog.Description>
                </Dialog.Header>

                <div class="grid gap-4 py-4">
                    <!-- Sampling strategy -->
                    <StrategySelect
                        value={samplingStrategy}
                        {isSimilaritySupported}
                        onValueChange={(v) => (samplingStrategy = v)}
                    />

                    {#if samplingStrategy === 'class_balancing'}
                        <ClassBalancingForm
                            {collectionId}
                            {balancingMode}
                            {classTargets}
                            {annotationCollections}
                            {annotationSourceId}
                            onBalancingModeChange={(mode) => (balancingMode = mode)}
                            onClassTargetsChange={(targets) => (classTargets = targets)}
                            onAnnotationSourceChange={(sourceId) => (annotationSourceId = sourceId)}
                        />
                    {/if}

                    {#if samplingStrategy === 'similarity'}
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
                            data-testid="sampling-dialog-n-samples-input"
                        />
                    </div>

                    <!-- Tag Name Input -->
                    <div class="grid grid-cols-4 items-center gap-4">
                        <Label for="tag-name" class="text-right text-foreground">Tag Name</Label>
                        <Input
                            id="tag-name"
                            type="text"
                            bind:value={samplingResultTagName}
                            class="col-span-3"
                            placeholder="Enter a tag for the sampled subset"
                            required
                            data-testid="sampling-dialog-tag-name-input"
                        />
                    </div>

                    <!-- Warning when no samples match the current filters -->
                    {#if noSamples}
                        <p
                            class="text-sm text-destructive"
                            data-testid="sampling-dialog-no-samples-warning"
                        >
                            No samples match the current filters.
                        </p>
                    {/if}

                    <!-- Warning when requesting more samples than available -->
                    {#if notEnoughSamples}
                        <p
                            class="text-sm text-destructive"
                            data-testid="sampling-dialog-not-enough-samples-warning"
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
                        onclick={closeSamplingDialog}
                        disabled={$isSubmitting}
                        data-testid="sampling-dialog-cancel"
                    >
                        Cancel
                    </Button>
                    <Tooltip content={!isFormValid ? validationErrorMessage : ''}>
                        <Button
                            type="submit"
                            disabled={!isFormValid ||
                                $isSubmitting ||
                                notEnoughSamples ||
                                noSamples}
                            data-testid="sampling-dialog-submit"
                        >
                            {$isSubmitting ? $loadingMessage || 'Creating...' : 'Create Sampling'}
                        </Button>
                    </Tooltip>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
