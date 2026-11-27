<script lang="ts">
    import { Select } from '$lib/components/Select';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Button } from '$lib/components/ui/button';
    import ThresholdInput from '$lib/components/SampleDetails/LabelWithModelPopUp/ThresholdInput/ThresholdInput.svelte';
    import { useBrowserModels } from '$lib/hooks';
    import ClassChecklist from '../ClassChecklist/ClassChecklist.svelte';

    interface Props {
        open: boolean;
        selectedCount: number;
        onStart: (params: { modelId: string; threshold: number; classNames: string[] }) => void;
    }

    let { open = $bindable(), selectedCount, onStart }: Props = $props();

    const DEFAULT_THRESHOLD = 0.5;
    const BYTES_PER_MB = 1_000_000;
    const { models, loadProgress, getDetector } = useBrowserModels();
    let modelId = $state($models[0].id);
    let threshold = $state(DEFAULT_THRESHOLD);
    // Every class is ticked by default.
    let excluded = $state(new Set<string>());

    const model = $derived($models.find((item) => item.id === modelId));
    const classNames = $derived(model?.class_names ?? []);
    const items = $derived($models.map((item) => ({ value: item.id, label: item.id })));
    const isLoading = $derived(classNames.length === 0);
    const keptClassNames = $derived(classNames.filter((name) => !excluded.has(name)));

    // The class list comes from the model file, so opening the dialog loads the model.
    $effect(() => {
        if (open) void getDetector(modelId);
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
            {#if isLoading}
                <p class="text-xs text-muted-foreground">
                    {#if $loadProgress}
                        Downloading model… {Math.round($loadProgress.loaded / BYTES_PER_MB)} of
                        {Math.round($loadProgress.total / BYTES_PER_MB)} MB
                    {:else}
                        Loading the model classes…
                    {/if}
                </p>
            {:else}
                <ClassChecklist
                    {classNames}
                    {excluded}
                    onExcludedChange={(next) => (excluded = next)}
                />
            {/if}
        </div>
        <Dialog.Footer>
            <Button disabled={isLoading || keptClassNames.length === 0} onclick={start}>
                Auto-label {selectedCount} images
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
