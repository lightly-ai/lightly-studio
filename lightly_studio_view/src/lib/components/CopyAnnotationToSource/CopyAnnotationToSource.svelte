<script lang="ts">
    import { Tooltip } from '$lib/components/ui/tooltip';
    import * as Popover from '$lib/components/ui/popover';
    import { useAnnotationCollections } from '$lib/hooks';
    import { CopyPlus } from '@lucide/svelte';
    import { useCopyAnnotationToSource } from './useCopyAnnotationToSource.svelte';

    type Props = ReturnType<Parameters<typeof useCopyAnnotationToSource>[0]>;
    const { collectionId, annotation, onCopied }: Props = $props();
    const sources = useAnnotationCollections(() => ({ collectionId }));
    const destinations = $derived(
        (sources.data ?? []).filter(
            (source) => source.collection_id !== annotation.annotation_collection_id
        )
    );
    const { copy, pending } = useCopyAnnotationToSource(() => ({
        collectionId,
        annotation,
        onCopied
    }));
    let open = $state(false);
</script>

<Popover.Root bind:open>
    <Tooltip content="Duplicate to another annotation source">
        <Popover.Trigger
            class="inline-flex size-7 items-center justify-center rounded-md hover:bg-accent disabled:opacity-50"
            disabled={$pending || !sources.isSuccess || !destinations.length}
            aria-label="Duplicate to another annotation source"
            ><CopyPlus class="size-4" /></Popover.Trigger
        >
    </Tooltip>
    <Popover.Content class="w-64 p-1" align="end">
        {#each destinations as destination (destination.collection_id)}
            <button
                type="button"
                class="w-full rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent"
                disabled={$pending}
                onclick={async () => {
                    if (await copy(destination.name)) open = false;
                }}>{destination.name}</button
            >
        {/each}
    </Popover.Content>
</Popover.Root>
