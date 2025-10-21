<script lang="ts">
    import { page } from '$app/state';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useCreateClassifiersPanel } from '$lib/hooks/useClassifiers/useCreateClassifiersPanel';
    import Button from '$lib/components/ui/button/button.svelte';
    import Input from '$lib/components/ui/input/input.svelte';
    import { useClassifiers } from '$lib/hooks/useClassifiers/useClassifiers';
    import { routeHelpers } from '$lib/routes';
    import { goto } from '$app/navigation';
    import { Alert } from '$lib/components/index.js';

    const { isCreateClassifiersPanelOpen, closeCreateClassifiersPanel } =
        useCreateClassifiersPanel();
    const { error, createClassifier } = useClassifiers();

    const { clearClassifierSamples } = useGlobalStorage();
    let classifierName = '';
    let datasetId = page.params.dataset_id;

    function handleClose() {
        clearClassifierSamples();
        classifierName = '';
        closeCreateClassifiersPanel();
        goto(routeHelpers.toSamples(datasetId));
    }
</script>

{#if $isCreateClassifiersPanelOpen}
    <div class="flex w-80 flex-col rounded-[1vw] bg-card p-4">
        <div class="mb-5 mt-2 flex items-center justify-between">
            <div class="text-lg font-semibold">Create Classifier</div>
            <Button variant="ghost" size="icon" onclick={handleClose} class="h-8 w-8">✕</Button>
        </div>
        <Separator class="mb-4 bg-border-hard" />
        <div class="flex-1 space-y-6">
            {#if $error}
                <Alert title="Error occured">{$error}</Alert>
            {/if}
            <div class="space-y-2">
                <label for="classifier-name" class="text-sm font-medium"> Classifier Name </label>
                <Input
                    id="classifier-name"
                    type="text"
                    placeholder="Enter classifier name"
                    bind:value={classifierName}
                />
            </div>
            <Button
                variant="default"
                class="w-full"
                onclick={() =>
                    createClassifier({
                        name: classifierName,
                        class_list: ['positive', 'negative'],
                        dataset_id: datasetId
                    })}
                disabled={!classifierName.trim()}
            >
                Create Classifier
            </Button>
        </div>
    </div>
{:else}
    <!-- Empty div to hold the space when panel is closed -->
    <div class="hidden"></div>
{/if}
