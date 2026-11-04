<script lang="ts">
    import { onMount, untrack } from 'svelte';
    import * as Command from '$lib/components/ui/command/index.js';
    import { matchClasses } from '../AnnotationCard/annotationCard.helpers';

    let {
        names,
        recent,
        initialQuery = '',
        onPick,
        onCancel
    }: {
        names: string[];
        recent: string[];
        initialQuery?: string;
        onPick: (className: string) => void;
        onCancel: () => void;
    } = $props();

    let query = $state(untrack(() => initialQuery));
    let highlighted = $state('');
    let inputRef = $state<HTMLInputElement | null>(null);

    const result = $derived(matchClasses({ names, recent, query }));
    const rows = $derived([
        ...result.matches.map((name) => ({ value: `class:${name}`, name, label: name })),
        ...(result.createName === null
            ? []
            : [
                  {
                      value: 'create',
                      name: result.createName,
                      label: `Create '${result.createName}'`
                  }
              ])
    ]);

    // The first row stays highlighted after every query change so Enter picks it.
    $effect(() => {
        highlighted = rows[0]?.value ?? '';
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
        placeholder="Pick a class"
        bind:value={query}
        bind:ref={inputRef}
        onkeydown={handleKeyDown}
    />
    <Command.List>
        {#each rows as row (row.value)}
            <Command.Item value={row.value} onSelect={() => onPick(row.name)}>
                {row.label}
            </Command.Item>
        {/each}
    </Command.List>
    <div class="px-2 py-1.5 text-xs text-muted-foreground">Esc to go back</div>
</Command.Root>
