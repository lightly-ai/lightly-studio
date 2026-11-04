<script lang="ts">
    import { onMount } from 'svelte';
    import * as Command from '$lib/components/ui/command/index.js';
    import { matchSources } from '../AnnotationCard/annotationCard.helpers';

    let {
        sources,
        excludeSourceId,
        onPick,
        onCancel
    }: {
        sources: { collection_id: string; name: string }[];
        excludeSourceId?: string;
        onPick: (sourceName: string) => void;
        onCancel: () => void;
    } = $props();

    let query = $state('');
    let highlighted = $state('');
    let inputRef = $state<HTMLInputElement | null>(null);

    const matches = $derived(
        matchSources({
            sources: sources.filter((source) => source.collection_id !== excludeSourceId),
            query
        })
    );

    // The first row stays highlighted after every query change so Enter picks it.
    $effect(() => {
        highlighted = matches[0]?.collection_id ?? '';
    });

    onMount(() => inputRef?.focus());

    const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Escape') return;
        event.preventDefault();
        event.stopPropagation();
        onCancel();
    };
</script>

<Command.Root shouldFilter={false} bind:value={highlighted}>
    <Command.Input
        placeholder="Pick a source"
        bind:value={query}
        bind:ref={inputRef}
        onkeydown={handleKeyDown}
    />
    <Command.List>
        {#if matches.length === 0}
            <div class="py-6 text-center text-sm">No annotation source matches</div>
        {/if}
        {#each matches as source (source.collection_id)}
            <Command.Item value={source.collection_id} onSelect={() => onPick(source.name)}>
                {source.name}
            </Command.Item>
        {/each}
    </Command.List>
    <div class="px-2 py-1.5 text-xs text-muted-foreground">Esc to go back</div>
</Command.Root>
