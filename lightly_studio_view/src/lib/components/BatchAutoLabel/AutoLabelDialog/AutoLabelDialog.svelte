<script lang="ts">
    import { Select } from '$lib/components/Select';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Button } from '$lib/components/ui/button';
    import ThresholdInput from '$lib/components/SampleDetails/LabelWithModelPopUp/ThresholdInput/ThresholdInput.svelte';
    import { useBrowserModels } from '$lib/hooks';
    import PromptClassesInput from '$lib/components/SampleDetails/LabelWithModelPopUp/PromptClassesInput/PromptClassesInput.svelte';
    import ClassChecklist from '../ClassChecklist/ClassChecklist.svelte';

    interface Props {
        open: boolean;
        selectedCount: number;
        onStart: (params: { modelId: string; threshold: number; classNames: string[] }) => void;
    }

    let { open = $bindable(), selectedCount, onStart }: Props = $props();

    const DEFAULT_THRESHOLD = 0.5;
    const BYTES_PER_MB = 1_000_000;
    const { models, loadProgress, getDetector, setPromptClassNames } = useBrowserModels();
    let modelId = $state($models[0].id);
    let threshold = $state(DEFAULT_THRESHOLD);
    // Every class is ticked by default.
    let excluded = $state(new Set<string>());

    const model = $derived($models.find((item) => item.id === modelId));
    const classNames = $derived(model?.class_names ?? []);
    const items = $derived($models.map((item) => ({ value: item.id, label: item.id })));
    // Set when loading the model failed, for the model it names.
    let loadFailure = $state<{ modelId: string; message: string } | null>(null);
    const loadError = $derived(loadFailure?.modelId === modelId ? loadFailure.message : null);
    const isTextPrompted = $derived(model?.isTextPrompted ?? false);
    const isLoading = $derived(classNames.length === 0 && loadError === null && !isTextPrompted);
    const keptClassNames = $derived(classNames.filter((name) => !excluded.has(name)));

    // The class list comes from the model file, so opening the dialog loads the model. A
    // text-prompted model has no class list and loads early, so the run starts sooner.
    $effect(() => {
        if (!open) return;
        const loadingModelId = modelId;
        const isLoadingTextPrompted = isTextPrompted;
        getDetector(loadingModelId)
            .then(({ classNames: loaded }) => {
                if (loaded.length > 0 || isLoadingTextPrompted) return;
                loadFailure = { modelId: loadingModelId, message: 'it has no class names.' };
            })
            .catch((error: unknown) => {
                const message = error instanceof Error ? error.message : String(error);
                loadFailure = { modelId: loadingModelId, message };
            });
    });

    const selectModel = (value: string) => {
        modelId = value;
        excluded = new Set();
    };

    const start = () => {
        onStart({ modelId, threshold, classNames: keptClassNames });
        open = false;
    };
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="max-w-md">
        <Dialog.Header>
            <Dialog.Title>Auto-label {selectedCount} images</Dialog.Title>
            <Dialog.Description>
                Runs in this browser. Keep the tab open while it runs.
            </Dialog.Description>
        </Dialog.Header>
        <div class="flex flex-col gap-3">
            <Select {items} value={modelId} size="sm" onValueChange={selectModel} />
            <ThresholdInput value={threshold} onChange={(value) => (threshold = value)} />
            {#if isTextPrompted}
                {#key modelId}
                    <PromptClassesInput
                        {classNames}
                        onChange={(names) => setPromptClassNames(modelId, names)}
                    />
                {/key}
            {/if}
            {#if loadError}
                <p class="text-xs text-destructive">Could not load the model: {loadError}</p>
            {:else if isLoading || $loadProgress?.modelId === modelId}
                <p class="text-xs text-muted-foreground">
                    {#if $loadProgress}
                        Downloading model… {Math.round($loadProgress.loaded / BYTES_PER_MB)} of
                        {Math.round($loadProgress.total / BYTES_PER_MB)} MB
                    {:else}
                        Loading the model classes…
                    {/if}
                </p>
            {:else if !isTextPrompted}
                <ClassChecklist
                    {classNames}
                    {excluded}
                    onExcludedChange={(next) => (excluded = next)}
                />
            {/if}
        </div>
        <Dialog.Footer>
            <Button disabled={keptClassNames.length === 0} onclick={start}>
                Auto-label {selectedCount} images
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
