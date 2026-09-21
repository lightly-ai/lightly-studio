<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { get } from 'svelte/store';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Button } from '$lib/components/ui/button';
    import { useAutoLabelDialog } from '$lib/hooks/useAutoLabelDialog';
    import { useGlobalStorage } from '$lib/hooks';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import AutoLabelConfig from './AutoLabelConfig.svelte';
    import AutoLabelSummary from './AutoLabelSummary.svelte';
    import { autoLabelError, useAutoLabelRun } from './useAutoLabelRun.svelte';
    import { supportsTask } from './AutoLabelDialog.helpers';

    const { isAutoLabelDialogOpen, closeAutoLabelDialog } = useAutoLabelDialog();
    const { filteredSampleCount, setLastGridType } = useGlobalStorage();
    const { imageFilter } = useImageFilters();
    const { setSelectedCollectionIds } = useAnnotationCollectionsFilter();
    const { description, run } = useAutoLabelRun();
    let task = $state<'' | 'object_detection' | 'segmentation'>('');
    let prompts = $state<string[]>([]);
    let overrides = $state<Record<string, string>>({});
    let threshold = $state(0.5);
    const collectionId = page.params.collection_id!;
    const gridPath = `/datasets/${page.params.dataset_id}/${page.params.collection_type}/${collectionId}/images`;
    const canRun = $derived(
        description.data?.ready &&
            !description.isFetching &&
            description.data.supported_conditioning.includes('targets') &&
            task &&
            supportsTask({ capabilities: description.data.capabilities, task }) &&
            prompts.length > 0 &&
            $filteredSampleCount > 0 &&
            !run.isPending
    );

    function submit(event: SubmitEvent) {
        event.preventDefault();
        if (!canRun || !task) return;
        run.mutate({
            collection_id: collectionId,
            filter: get(imageFilter),
            task,
            targets: prompts.map((prompt) => ({
                prompt,
                class_name: overrides[prompt]?.trim() || prompt
            })),
            confidence_threshold: threshold
        });
    }
    async function close() {
        if (run.isPending) return;
        if (run.data) {
            setSelectedCollectionIds([run.data.source_id]);
            setLastGridType('images');
            await goto(gridPath);
        }
        closeAutoLabelDialog();
    }
</script>

<Dialog.Root
    open={$isAutoLabelDialogOpen}
    onOpenChange={(open) => {
        if (!open) void close();
    }}
>
    <Dialog.Content
        class="max-h-[90vh] w-[calc(100%-2rem)] overflow-y-auto sm:max-w-[540px]"
        onEscapeKeydown={(event) => {
            if (run.isPending) event.preventDefault();
        }}
        onInteractOutside={(event) => {
            if (run.isPending) event.preventDefault();
        }}
    >
        <Dialog.Header>
            <Dialog.Title>{run.data ? 'Auto-labeling complete' : 'Auto-label images'}</Dialog.Title>
            <Dialog.Description
                >{run.data
                    ? 'Run results'
                    : `${$filteredSampleCount} images matching current filters`}</Dialog.Description
            >
        </Dialog.Header>
        {#if run.data}
            <AutoLabelSummary summary={run.data} />
            <Dialog.Footer><Button onclick={close}>View results</Button></Dialog.Footer>
        {:else if run.isPending}
            <p role="status" class="py-8 text-sm">
                Auto-labeling in progress. This may take several minutes.
            </p>
        {:else}
            <form onsubmit={submit} class="grid gap-5">
                <AutoLabelConfig
                    {description}
                    bind:task
                    bind:prompts
                    bind:overrides
                    bind:threshold
                />
                {#if run.isError}<p role="alert" class="text-sm text-destructive-text">
                        {autoLabelError(run.error)}
                    </p>{/if}
                <Dialog.Footer>
                    <Button type="button" variant="outline" onclick={close}>Cancel</Button>
                    <Button type="submit" disabled={!canRun}>Auto-label</Button>
                </Dialog.Footer>
            </form>
        {/if}
    </Dialog.Content>
</Dialog.Root>
