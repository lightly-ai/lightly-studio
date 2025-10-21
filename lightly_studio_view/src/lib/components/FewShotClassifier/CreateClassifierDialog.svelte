<script lang="ts">
    import { page } from '$app/state';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useCreateClassifiersPanel } from '$lib/hooks/useClassifiers/useCreateClassifiersPanel';
    import { useClassifiers } from '$lib/hooks/useClassifiers/useClassifiers';
    import { Alert } from '$lib/components/index.js';
    import ClassifierSamplesGrid from './ClassifierSamplesGrid.svelte';
    import NetworkIcon from '@lucide/svelte/icons/network';
    import { handleCreateClassifierClose } from './classifierDialogHelpers';

    const { isCreateClassifiersPanelOpen, closeCreateClassifiersPanel } = useCreateClassifiersPanel();
    const { error, createClassifier } = useClassifiers();
    const { clearClassifierSamples } = useGlobalStorage();
    
    let classifierName = $state('');
    let datasetId = page.params.dataset_id;
    let isSubmitting = $state(false);

    // Form validation
    const isFormValid = $derived(classifierName.trim().length > 0);

    function handleClose() {
        handleCreateClassifierClose(datasetId, classifierName, (name) => classifierName = name);
    }

    async function handleFormSubmit(event: Event) {
        event.preventDefault();
        if (!isFormValid || isSubmitting) return;

        isSubmitting = true;
        try {
            await createClassifier({
                name: classifierName,
                class_list: ['positive', 'negative'],
                dataset_id: datasetId
            });
        } finally {
            isSubmitting = false;
        }
    }
</script>

<Dialog.Root bind:open={$isCreateClassifiersPanelOpen} onOpenChange={(open) => !open && handleClose()}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[800px] sm:max-h-[90vh]">
            <form onsubmit={handleFormSubmit}>
                <Dialog.Header>
                    <Dialog.Title class="text-foreground flex items-center gap-2">
                        <NetworkIcon class="size-5" />
                        Create Classifier
                    </Dialog.Title>
                    <Dialog.Description class="text-foreground">
                        Create a new few-shot classifier providing positive and negative examples. Selected samples are considered positive examples and unselected samples are considered negative examples.
                    </Dialog.Description>
                </Dialog.Header>

                <div class="grid gap-4 py-4">
                    {#if $error}
                        <Alert title="Error occurred">{$error}</Alert>
                    {/if}

                    <div class="grid grid-cols-4 items-center gap-4">
                        <Label for="classifier-name" class="text-right text-foreground">
                            Classifier Name
                        </Label>
                        <Input
                            id="classifier-name"
                            type="text"
                            bind:value={classifierName}
                            class="col-span-3"
                            placeholder="Enter classifier name"
                            required
                            data-testid="classifier-name-input"
                        />
                    </div>
                </div>

                <!-- Samples Grid -->
                <div class="border-t pt-4">
                    <h3 class="mb-4 text-lg font-semibold">Select Positive Examples</h3>
                    <div class="h-[400px] w-full rounded-lg border">
                        <ClassifierSamplesGrid dataset_id={datasetId} />
                    </div>
                </div>

                <Dialog.Footer>
                    <button
                        type="button"
                        class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
                        onclick={handleClose}
                        disabled={isSubmitting}
                        data-testid="classifier-dialog-cancel"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
                        disabled={!isFormValid || isSubmitting}
                        data-testid="classifier-dialog-submit"
                    >
                        {isSubmitting ? 'Creating...' : 'Create Classifier'}
                    </button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
