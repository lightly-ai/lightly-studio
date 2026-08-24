<script lang="ts">
    import { page } from '$app/state';
    import { Alert } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useClassifierState } from '$lib/hooks/useClassifiers/useClassifierState';
    import { useClassifiers } from '$lib/hooks/useClassifiers/useClassifiers';
    import { useClassifierWorkflow } from '$lib/hooks/useClassifiers/useClassifierWorkflow';
    import { Network as NetworkIcon } from '@lucide/svelte';
    import ClassifierWorkflowGuidance from './ClassifierWorkflowGuidance.svelte';
    import CreateClassifierDialog from './CreateClassifierDialog.svelte';
    import RefineClassifierDialog from './RefineClassifierDialog.svelte';

    const { workflow, isOpen, close } = useClassifierWorkflow();
    const { dropTempClassifier } = useClassifiers();
    const { clearClassifierSamples, clearClassifierSelectedSamples } = useClassifierState();
    const { clearSelectedSamples } = useGlobalStorage();
    const collectionId = page.params.collection_id!;
    let closeError = $state<string | null>(null);
    let isClosing = $state(false);

    function finishWorkflow() {
        if ($workflow.phase === 'refine') clearSelectedSamples(collectionId);
        clearClassifierSamples();
        clearClassifierSelectedSamples();
        close();
    }

    async function cancelWorkflow() {
        if (isClosing || $workflow.isPending) return;

        isClosing = true;
        closeError = null;
        try {
            if ($workflow.mode === 'temp' && $workflow.classifierId) {
                await dropTempClassifier($workflow.classifierId);
            }
            finishWorkflow();
        } catch (error) {
            closeError = error instanceof Error ? error.message : String(error);
        } finally {
            isClosing = false;
        }
    }
</script>

<Dialog.Root open={$isOpen} onOpenChange={(open) => !open && cancelWorkflow()}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            data-testid="classifier-workflow-dialog"
            class="flex h-[90vh] flex-col overflow-hidden border-border bg-background dark:[color-scheme:dark] sm:max-h-[90vh] sm:max-w-[800px]"
        >
            <Dialog.Header>
                <Dialog.Title class="flex items-center gap-2 text-foreground">
                    <NetworkIcon class="size-5" />
                    Find Similar Images
                </Dialog.Title>
                <Dialog.Description class="text-foreground">
                    {#if $workflow.phase === 'create'}
                        Create a classifier by showing LightlyStudio what you want to find.
                    {:else}
                        Reviewing classifier:
                        <span class="font-medium">{$workflow.classifierName}</span>
                    {/if}
                </Dialog.Description>
            </Dialog.Header>

            <ClassifierWorkflowGuidance
                phase={$workflow.phase}
                isTemporary={$workflow.mode !== 'existing'}
            />
            {#if closeError}
                <Alert title="Failed to cancel classifier">{closeError}</Alert>
            {/if}

            <div class="flex min-h-0 flex-1 flex-col overflow-hidden py-4">
                {#if $workflow.phase === 'create'}
                    <CreateClassifierDialog onCancel={cancelWorkflow} />
                {:else if $workflow.phase === 'refine'}
                    <RefineClassifierDialog onCancel={cancelWorkflow} onFinish={finishWorkflow} />
                {/if}
            </div>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
