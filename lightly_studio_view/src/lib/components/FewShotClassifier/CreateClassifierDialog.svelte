<script lang="ts">
    import { page } from '$app/state';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import { useCreateClassifiersPanel } from '$lib/hooks/useClassifiers/useCreateClassifiersPanel';
    import { useClassifiers } from '$lib/hooks/useClassifiers/useClassifiers';
    import { Alert, Button } from '$lib/components';
    import ClassifierSamplesGrid from './ClassifierSamplesGrid.svelte';
    import { Network as NetworkIcon } from '@lucide/svelte';
    import { handleCreateClassifierClose } from './classifierDialogHelpers';

    const { isCreateClassifiersPanelOpen } = useCreateClassifiersPanel();
    const { createClassifier } = useClassifiers();

    let classifierName = $state('');
    let collectionId = page.params.collection_id;
    let isSubmitting = $state(false);
    let submitError = $state<string | null>(null);

    // Form validation
    const isFormValid = $derived(classifierName.trim().length > 0);

    function handleClose() {
        classifierName = '';
        handleCreateClassifierClose();
        submitError = null;
    }

    async function handleFormSubmit(event: Event) {
        event.preventDefault();
        if (!isFormValid || isSubmitting) return;

        isSubmitting = true;
        submitError = null; // Clear any previous errors

        try {
            await createClassifier({
                name: classifierName,
                class_list: ['positive', 'negative'],
                collection_id: collectionId
            });
            classifierName = '';
        } catch (err) {
            // Set the actual error message from the caught error
            submitError = err instanceof Error ? err.message : String(err);
        } finally {
            isSubmitting = false;
        }
    }
</script>

<Dialog.Root
    bind:open={$isCreateClassifiersPanelOpen}
    onOpenChange={(open) => !open && handleClose()}
>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            class="h-[90vh] overflow-y-auto border-border bg-background dark:[color-scheme:dark] sm:max-h-[90vh] sm:max-w-[800px]"
        >
            <Dialog.Header>
                <Dialog.Title class="flex items-center gap-2 text-foreground">
                    <NetworkIcon class="size-5" />
                    Create Classifier
                </Dialog.Title>
                <Dialog.Description class="text-foreground">
                    Create a new few-shot classifier providing positive and negative examples.
                    Selected samples are considered positive examples and unselected samples are
                    considered negative examples.
                </Dialog.Description>
            </Dialog.Header>

            <div class="grid gap-4 py-4">
                {#if submitError}
                    <Alert title="Failed to create classifier">
                        {submitError}
                    </Alert>
                {/if}
                <div class="flex items-center gap-4">
                    <Label
                        for="classifier-name"
                        class="whitespace-nowrap text-left text-foreground"
                    >
                        Classifier Name
                    </Label>
                    <Input
                        id="classifier-name"
                        type="text"
                        bind:value={classifierName}
                        class="flex-1"
                        placeholder="Enter classifier name"
                        required
                        data-testid="classifier-name-input"
                    />
                </div>
            </div>

            <!-- Samples Grid -->
            <div class="flex min-h-0 flex-1 flex-col border-t pt-4">
                <h3 class="mb-4 text-lg font-semibold">Select Positive Examples</h3>
                <div
                    class="min-h-0 w-full flex-1 overflow-y-auto rounded-lg border dark:[color-scheme:dark]"
                >
                    <ClassifierSamplesGrid collection_id={collectionId} />
                </div>
            </div>

            <Dialog.Footer class="flex flex-nowrap gap-4">
                <Button
                    variant="outline"
                    buttonProps={{
                        onclick: handleClose,
                        disabled: isSubmitting,
                        'data-testid': 'classifier-dialog-cancel',
                        class: 'shrink-0'
                    }}
                >
                    Cancel
                </Button>
                <Button
                    isPending={isSubmitting}
                    buttonProps={{
                        onclick: handleFormSubmit,
                        disabled: !isFormValid || isSubmitting,
                        'data-testid': 'classifier-dialog-submit',
                        class: 'shrink-0'
                    }}
                >
                    {isSubmitting ? 'Creating...' : 'Create Classifier'}
                </Button>
            </Dialog.Footer>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
