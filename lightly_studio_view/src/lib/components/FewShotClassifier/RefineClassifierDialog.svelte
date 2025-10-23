<script lang="ts">
    import { page } from '$app/state';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Label } from '$lib/components/ui/label';
    import { Switch } from '$lib/components/ui/switch';
    import { useRefineClassifiersPanel } from '$lib/hooks/useClassifiers/useRefineClassifiersPanel';
    import { useClassifiers } from '$lib/hooks/useClassifiers/useClassifiers';
    import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
    import { Alert } from '$lib/components/index.js';
    import ClassifierSamplesGrid from './ClassifierSamplesGrid.svelte';
    import NetworkIcon from '@lucide/svelte/icons/network';
    import { handleRefineClassifierClose } from './classifierDialogHelpers';

    const showTrainingSamplesToggle = useSessionStorage<boolean>(
        'refine_classifier_show_training_samples',
        false
    );
    const {
        isRefineClassifiersPanelOpen,
        currentMode,
        currentClassifierId,
        currentClassifierName,
        currentClassifierClasses
    } = useRefineClassifiersPanel();
    const { error, commitTempClassifier, refineClassifier, showClassifierTrainingSamples } =
        useClassifiers();

    let datasetId = page.params.dataset_id;
    let isSubmitting = $state(false);

    function handleClose() {
        handleRefineClassifierClose();
    }

    async function handleRefineClassifier() {
        if (isSubmitting) return;

        isSubmitting = true;
        try {
            showTrainingSamplesToggle.set(false);
            await refineClassifier(
                $currentClassifierId || '',
                datasetId,
                $currentClassifierClasses || []
            );
        } finally {
            isSubmitting = false;
        }
    }

    async function handleCommitTempClassifier() {
        if (isSubmitting) return;

        isSubmitting = true;
        try {
            showTrainingSamplesToggle.set(false);
            await commitTempClassifier($currentClassifierId || '', datasetId);
            handleClose();
        } finally {
            isSubmitting = false;
        }
    }

    function handleShowTrainingSamples(checked: boolean) {
        showTrainingSamplesToggle.set(checked);
        showClassifierTrainingSamples(
            $currentClassifierId || '',
            datasetId,
            $currentClassifierClasses || [],
            checked
        );
    }
</script>

<Dialog.Root
    bind:open={$isRefineClassifiersPanelOpen}
    onOpenChange={(open) => !open && handleClose()}
>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            class="overflow-y-auto border-border bg-background dark:[color-scheme:dark] sm:max-h-[90vh] sm:max-w-[800px]"
        >
            <Dialog.Header>
                <Dialog.Title class="flex items-center gap-2 text-foreground">
                    <NetworkIcon class="size-5" />
                    {$currentMode === 'temp' ? 'Refine Temporary Classifier' : 'Refine Classifier'}
                </Dialog.Title>
                <Dialog.Description class="text-foreground">
                    You are refining classifier: <span class="font-medium"
                        >{$currentClassifierName}</span
                    >
                </Dialog.Description>
            </Dialog.Header>

            <div class="grid gap-4 py-4">
                {#if $error}
                    <Alert title="Error occurred">{$error}</Alert>
                {/if}

                <!-- Instructions -->
                <div class="space-y-4">
                    <div>
                        <h3 class="mb-2 text-lg font-semibold">Refinement Instructions</h3>
                        <ol
                            class="list-inside list-decimal space-y-2 text-sm text-muted-foreground"
                        >
                            <li>
                                Select positive examples from the samples below. Not selected
                                samples are considered negative examples.
                            </li>
                            <li>Click "Refine Classifier" to retrain with your selections</li>
                            {#if $currentMode === 'temp'}
                                <li>
                                    Once satisfied with the results, click "Save Classifier" to save
                                    permanently
                                </li>
                            {/if}
                        </ol>
                    </div>
                </div>
            </div>

            <!-- Samples Grid -->
            <div class="border-t pt-4">
                <h3 class="mb-4 text-lg font-semibold">Select Positive Examples</h3>
                <div
                    class="h-[400px] w-full overflow-y-auto rounded-lg border dark:[color-scheme:dark]"
                >
                    <ClassifierSamplesGrid dataset_id={datasetId} />
                </div>
            </div>

            <Dialog.Footer class="flex flex-col gap-4">
                <!-- Show All Training Samples Toggle -->
                <div class="flex items-center gap-4">
                    <Label class="text-foreground">Show All Training Samples</Label>
                    <Switch
                        checked={$showTrainingSamplesToggle}
                        onCheckedChange={handleShowTrainingSamples}
                        class=""
                    />
                </div>

                <!-- Action Buttons -->
                <div class="flex gap-2">
                    {#if $currentMode === 'temp'}
                        <button
                            type="button"
                            class="inline-flex h-10 items-center justify-center whitespace-nowrap rounded-md border border-input bg-background px-4 py-2 text-sm font-medium ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
                            onclick={handleCommitTempClassifier}
                            disabled={isSubmitting}
                            data-testid="commit-temp-classifier-button"
                        >
                            {isSubmitting ? 'Committing...' : 'Save Classifier'}
                        </button>
                    {/if}

                    <button
                        type="button"
                        class="inline-flex h-10 items-center justify-center whitespace-nowrap rounded-md border border-input bg-background px-4 py-2 text-sm font-medium ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
                        onclick={handleClose}
                        disabled={isSubmitting}
                        data-testid="refine-dialog-cancel"
                    >
                        Cancel
                    </button>

                    <button
                        type="button"
                        class="inline-flex h-10 items-center justify-center whitespace-nowrap rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground ring-offset-background transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
                        onclick={handleRefineClassifier}
                        disabled={isSubmitting}
                        data-testid="refine-classifier-button"
                    >
                        {isSubmitting ? 'Refining...' : 'Refine Classifier'}
                    </button>
                </div>
            </Dialog.Footer>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
