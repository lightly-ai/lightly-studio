<script lang="ts">
    import { page } from '$app/state';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import Button from '$lib/components/ui/button/button.svelte';
    import { useRefineClassifiersPanel } from '$lib/hooks/useClassifiers/useRefineClassifiersPanel';
    import { useClassifiers } from '$lib/hooks/useClassifiers/useClassifiers';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
    import { routeHelpers } from '$lib/routes';
    import { goto } from '$app/navigation';
    import { Alert } from '$lib/components/index.js';
    import Label from '../ui/label/label.svelte';
    import { Switch } from '$lib/components/ui/switch';
    const { clearSelectedSamples } = useGlobalStorage();
    const showTrainingSamplesToggle = useSessionStorage<boolean>(
        'refine_classifier_show_training_samples',
        false
    );
    const {
        isRefineClassifiersPanelOpen,
        closeRefineClassifiersPanel,
        currentMode,
        currentClassifierId,
        currentClassifierName,
        currentClassifierClasses
    } = useRefineClassifiersPanel();
    const { error, commitTempClassifier, refineClassifier, showClassifierTrainingSamples } =
        useClassifiers();

    let datasetId = page.params.dataset_id;
    function handleClose() {
        clearSelectedSamples();
        showTrainingSamplesToggle.set(false);
        closeRefineClassifiersPanel();
        goto(routeHelpers.toSamples(datasetId));
    }
</script>

{#if $isRefineClassifiersPanelOpen}
    <div class="flex w-80 flex-col rounded-[1vw] bg-card p-4">
        <div class="mb-5 mt-2 flex items-center justify-between">
            <div class="text-lg font-semibold">
                {$currentMode === 'temp' ? 'Refine Temporary Classifier' : 'Refine Classifier'}
            </div>
            <Button variant="ghost" size="icon" onclick={handleClose} class="h-8 w-8">✕</Button>
        </div>
        <Separator class="mb-4 bg-border-hard" />
        <div class="flex-1 space-y-6">
            <div class="space-y-4">
                <div>
                    <h3 class="mb-2 text-lg font-semibold">Refinement Instructions</h3>
                    <p class="mb-4 text-sm text-muted-foreground">
                        You are refining classifier: <span class="font-medium"
                            >{$currentClassifierName}</span
                        >
                    </p>
                    <ol class="list-inside list-decimal space-y-2 text-sm text-muted-foreground">
                        <li>Select positive examples from the samples</li>
                        <li>Click "Refine Classifier" to retrain with your selections</li>
                        {#if $currentMode === 'temp'}
                            <li>
                                Once satisfied with the results, click "Commit Temporary Classifier"
                                to save permanently
                            </li>
                        {/if}
                    </ol>
                </div>
            </div>
            <div class="space-y-4">
                {#if $error}
                    <Alert title="Error occured">{$error}</Alert>
                {/if}
                <Button
                    variant="default"
                    class="w-full"
                    onclick={() => {
                        showTrainingSamplesToggle.set(false);
                        refineClassifier(
                            $currentClassifierId || '',
                            datasetId,
                            $currentClassifierClasses || []
                        );
                    }}
                >
                    Refine Classifier
                </Button>
                <div class="flex items-center justify-between gap-4">
                    <Label class="text-foreground">Show All Training Samples</Label>
                    <Switch
                        class=""
                        checked={$showTrainingSamplesToggle}
                        onCheckedChange={(checked: boolean) => {
                            showTrainingSamplesToggle.set(checked);
                            showClassifierTrainingSamples(
                                $currentClassifierId || '',
                                datasetId,
                                $currentClassifierClasses || [],
                                checked
                            );
                        }}
                    />
                </div>
                {#if $currentMode === 'temp'}
                    <Button
                        variant="outline"
                        class="w-full"
                        onclick={() => {
                            showTrainingSamplesToggle.set(false);
                            commitTempClassifier($currentClassifierId || '', datasetId);
                        }}
                    >
                        Commit Temporary Classifier
                    </Button>
                {/if}
            </div>
        </div>
    </div>
{:else}
    <div class="hidden"></div>
{/if}
