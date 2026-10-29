<script lang="ts">
    import { Tooltip } from '$lib/components/ui/tooltip';
    import * as Command from '$lib/components/ui/command';
    import * as Popover from '$lib/components/ui/popover';
    import { useAnnotationCollections } from '$lib/hooks';
    import { cn } from '$lib/utils';
    import type { Component } from 'svelte';

    interface Props {
        /** The collection that owns the annotation sources. */
        collectionId: string;
        /** The source to leave out of the list, usually the current source. */
        excludeSourceId?: string;
        /** Tooltip and accessible name of the trigger. */
        label: string;
        /** Heading of the source list, e.g. "Move to". */
        heading: string;
        icon: Component<{ class?: string }>;
        /** When set, the trigger shows this text next to the icon. */
        triggerText?: string;
        disabled?: boolean;
        /** Called with the picked or typed source name. Return true to close the picker. */
        onPick: (sourceName: string) => Promise<boolean>;
    }

    const {
        collectionId,
        excludeSourceId,
        label,
        heading,
        icon: Icon,
        triggerText,
        disabled = false,
        onPick
    }: Props = $props();
    const sources = useAnnotationCollections(() => ({ collectionId }));
    const destinations = $derived(
        (sources.data ?? []).filter((source) => source.collection_id !== excludeSourceId)
    );
    let open = $state(false);
    let name = $state('');
    const trimmedName = $derived(name.trim());
    const exists = $derived(sources.data?.some((source) => source.name === trimmedName));

    async function pick(sourceName: string) {
        if (await onPick(sourceName)) {
            name = '';
            open = false;
        }
    }
</script>

<Popover.Root bind:open>
    <Tooltip content={label} triggerClass="flex" noTriggerRole>
        <Popover.Trigger
            class={cn(
                'inline-flex items-center justify-center gap-2 rounded-md hover:bg-accent disabled:opacity-50',
                triggerText ? 'h-9 w-full border px-3 text-sm' : 'size-7'
            )}
            disabled={disabled || !sources.isSuccess}
            aria-label={label}
            onclick={(event) => event.stopPropagation()}
        >
            <Icon class="size-4" />
            {#if triggerText}{triggerText}{/if}
        </Popover.Trigger>
    </Tooltip>
    <Popover.Content class="w-64 p-0" align="end">
        <Command.Root label="Annotation source">
            <Command.Input placeholder="Search or create a source…" bind:value={name} {disabled} />
            <Command.List>
                <Command.Group {heading}>
                    {#each destinations as destination (destination.collection_id)}
                        <Command.Item
                            value={destination.name}
                            {disabled}
                            onSelect={() => pick(destination.name)}
                        >
                            {destination.name}
                        </Command.Item>
                    {/each}
                </Command.Group>
                {#if trimmedName && !exists}
                    <div class="border-t">
                        <Command.Item
                            value="__create__"
                            {disabled}
                            onSelect={() => pick(trimmedName)}
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
