<script lang="ts">
    import { Tooltip } from '$lib/components/ui/tooltip';
    import * as Command from '$lib/components/ui/command';
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
    let name = $state('');
    const trimmedName = $derived(name.trim());
    const exists = $derived(sources.data?.some((source) => source.name === trimmedName));

    async function duplicate(sourceName: string) {
        if ($pending || !sourceName) return;
        if (await copy(sourceName)) {
            name = '';
            open = false;
        }
    }
</script>

<Popover.Root bind:open>
    <Tooltip content="Duplicate to another annotation source" triggerClass="flex">
        <Popover.Trigger
            class="inline-flex size-7 items-center justify-center rounded-md hover:bg-accent disabled:opacity-50"
            disabled={$pending || !sources.isSuccess}
            aria-label="Duplicate to another annotation source"
            onclick={(event) => event.stopPropagation()}
            ><CopyPlus class="size-4" /></Popover.Trigger
        >
    </Tooltip>
    <Popover.Content class="w-64 p-0" align="end">
        <Command.Root label="Annotation source">
            <Command.Input
                placeholder="Search or create a source…"
                bind:value={name}
                disabled={$pending}
            />
            <Command.List>
                <Command.Group heading="Duplicate to">
                    {#each destinations as destination (destination.collection_id)}
                        <Command.Item
                            value={destination.name}
                            disabled={$pending}
                            onSelect={() => duplicate(destination.name)}
                        >
                            {destination.name}
                        </Command.Item>
                    {/each}
                </Command.Group>
                {#if trimmedName && !exists}
                    <div class="border-t">
                        <Command.Item
                            value="__create__"
                            disabled={$pending}
                            onSelect={() => duplicate(trimmedName)}
                            forceMount
                            keywords={[]}
                        >
                            <span class="opacity-50">Create:</span>
                            <span class="min-w-0 truncate font-semibold">{trimmedName}</span>
                        </Command.Item>
                    </div>
                {/if}
            </Command.List>
        </Command.Root>
    </Popover.Content>
</Popover.Root>
