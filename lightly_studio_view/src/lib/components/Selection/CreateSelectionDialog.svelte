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
    import WandSparklesIcon from '@lucide/svelte/icons/wand-sparkles';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import type {
        EmbeddingDiversityStrategy,
        MetadataWeightingStrategy
    } from '$lib/api/lightly_studio_local';

    // Get dataset ID from page context
    const datasetId = page.data.datasetId;

    const { loadTags } = useTags({ dataset_id: datasetId, kind: ['sample'] });

    // Dialog state
    let isOpen = $state(false);

    const SelectionStrategies = {
        DIVERSITY: 'diversity',
        TYPICALITY: 'typicality'
    };

    type Strategy =
        | ({
              strategy_name: 'diversity';
              embedding_model_name: string | null;
          } & EmbeddingDiversityStrategy)
        | ({
              strategy_name: 'weights';
              metadata_key: string;
          } & MetadataWeightingStrategy);

    // Form state
    let selectionStrategies = $state<string[]>([]);
    let nSamplesToSelect = $state<number>(10);
    let selectionResultTagName = $state<string>('');
    let isSubmitting = $state(false);
    let loadingMessage = $state<string>('');

    const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

    let selectedStrategiesDisplay = $derived(
        selectionStrategies.map(capitalize).join(', ') || 'Select strategy'
    );

    // Form validation
    const isFormValid = $derived(
        selectionStrategies.length > 0 &&
            nSamplesToSelect > 0 &&
            selectionResultTagName.trim().length > 0
    );

    function handleFormSubmit(event: Event) {
        event.preventDefault();
        if (!isFormValid) return;

        submitSelection();
    }

    function handleSelectionSuccess() {
        toast.success('Selection created successfully');
        loadTags();

        isOpen = false;

        selectionStrategies = [];
        nSamplesToSelect = 10;
        selectionResultTagName = '';
    }

    async function submitSelection() {
        isSubmitting = true;

        try {
            const strategies: Strategy[] = [];

            loadingMessage = 'Creating selection...';

            if (selectionStrategies.includes(SelectionStrategies.TYPICALITY)) {
                const typicalityResponse = await computeTypicalityMetadata({
                    path: { dataset_id: datasetId },
                    body: {
                        embedding_model_name: null,
                        metadata_name: SelectionStrategies.TYPICALITY
                    }
                });

                if (typicalityResponse.error) {
                    return toast.error(
                        'Failed to compute typicality metadata: ' +
                            (String(typicalityResponse.error.error) || 'Unknown error')
                    );
                }

                strategies.push({
                    strategy_name: 'weights',
                    metadata_key: SelectionStrategies.TYPICALITY
                });
            }

            if (selectionStrategies.includes(SelectionStrategies.DIVERSITY)) {
                strategies.push({
                    strategy_name: 'diversity',
                    embedding_model_name: null
                });
            }

            const response = await createCombinationSelection({
                path: { dataset_id: datasetId },
                body: {
                    n_samples_to_select: nSamplesToSelect,
                    selection_result_tag_name: selectionResultTagName,
                    strategies: strategies
                }
            });

            if (response.error) {
                toast.error(String(response.error.error) || 'Failed to create selection');
                return;
            }

            return handleSelectionSuccess();
        } catch (error) {
            toast.error('Failed to create selection: ' + (error as Error).message);
        } finally {
            isSubmitting = false;
            loadingMessage = '';
            selectionStrategies = [];
        }
    }
</script>

<Button
    variant="ghost"
    class="nav-button flex items-center space-x-2"
    onclick={() => (isOpen = true)}
    data-testid="selection-dialog-button"
    title="Create Selection"
>
    <WandSparklesIcon class="size-4" />
    <span>Create Selection</span>
</Button>

<Dialog.Root bind:open={isOpen}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[425px]">
            <form onsubmit={handleFormSubmit}>
                <Dialog.Header>
                    <Dialog.Title class="text-foreground">Create Selection</Dialog.Title>
                    <Dialog.Description class="text-foreground">
                        Create a subset of the whole dataset using the selected strategy. The
                        selected samples will be tagged with the provided tag name.
                    </Dialog.Description>
                </Dialog.Header>

                <div class="grid gap-4 py-4">
                    <!-- Strategy Selection -->
                    <div class="grid grid-cols-4 items-center gap-4">
                        <Label for="strategy" class="text-right text-foreground">Strategy</Label>
                        <Select.Root name="strategy" bind:value={selectionStrategies}>
                            <Select.Trigger
                                class="col-span-3"
                                data-testid="selection-dialog-strategy-select"
                            >
                                {selectedStrategiesDisplay}
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
                            placeholder="Enter tag name for results"
                            required
                            data-testid="selection-dialog-tag-name-input"
                        />
                    </div>
                </div>

                <Dialog.Footer>
                    <Button
                        variant="outline"
                        type="button"
                        onclick={() => (isOpen = false)}
                        disabled={isSubmitting}
                        data-testid="selection-dialog-cancel"
                    >
                        Cancel
                    </Button>
                    <Button
                        type="submit"
                        disabled={!isFormValid || isSubmitting}
                        data-testid="selection-dialog-submit"
                    >
                        {isSubmitting ? loadingMessage || 'Creating...' : 'Create Selection'}
                    </Button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
