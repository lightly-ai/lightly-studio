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

    // Get collection ID from page context
    const collectionId = $derived(page.data.collection?.collection_id ?? '');

    const { loadTags } = $derived(useTags({ collection_id: collectionId, kind: ['sample'] }));

    const { isSelectionDialogOpen, openSelectionDialog, closeSelectionDialog } =
        useSelectionDialog();

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

    function handleFormSubmit(event: Event) {
        event.preventDefault();
        if (!isFormValid) return;

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
                        ]
                    }
                });

                if (response.error) {
                    toast.error(String(response.error.detail) || 'Failed to create selection');
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

                if (typicalityResponse.error) {
                    toast.error(
                        'Failed to compute typicality metadata: ' +
                            (String(typicalityResponse.error.detail) || 'Unknown error')
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
                        ]
                    }
                });

                if (selectionResponse.error) {
                    toast.error(
                        String(selectionResponse.error.detail) || 'Failed to create selection'
                    );
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
                        Create a subset of the whole collection using the selected strategy. The
                        selected samples will be tagged with the provided tag name.
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
                        onclick={closeSelectionDialog}
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
