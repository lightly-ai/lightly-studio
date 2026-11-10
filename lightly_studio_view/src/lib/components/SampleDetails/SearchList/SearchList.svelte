<script lang="ts">
    import { onMount, type ComponentProps } from 'svelte';
    import * as Command from '$lib/components/ui/command/index.js';
    import { Kbd } from '$lib/components/ui/kbd';
    import { SearchListItem } from './SearchListItem';

    interface Props {
        /** The rows that match the query, best first. */
        rows: ComponentProps<typeof SearchListItem>['row'][];
        query?: string;
        /** The accessible name of the search. */
        label: string;
        placeholder: string;
        /** Heading above the rows, for example "Move to". */
        heading?: string;
        /** Shown above the rows while they load. */
        loadingMessage?: string;
        /** Shown when no row matches. */
        emptyMessage?: string;
        /** Whether Esc goes back to a previous view, so the list says so. */
        showBackHint?: boolean;
        disabled?: boolean;
        onCancel: () => void;
    }

    let {
        rows,
        query = $bindable(''),
        label,
        placeholder,
        heading,
        loadingMessage,
        emptyMessage,
        showBackHint = false,
        disabled = false,
        onCancel
    }: Props = $props();

    let highlighted = $state('');
    let inputRef = $state<HTMLInputElement | null>(null);

    // The first row that can be picked stays highlighted after every query change, so Enter
    // picks it.
    $effect(() => {
        highlighted = rows.find((row) => !row.disabled)?.value ?? '';
    });

    onMount(() => inputRef?.focus());

    const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Escape') return;
        event.preventDefault();
        event.stopPropagation();
        onCancel();
    };
</script>

<Command.Root {label} shouldFilter={false} bind:value={highlighted}>
    <Command.Input
        {placeholder}
        {disabled}
        bind:value={query}
        bind:ref={inputRef}
        onkeydown={handleKeyDown}
    />
    <Command.List>
        {#if loadingMessage}
            <Command.Loading>{loadingMessage}</Command.Loading>
        {:else if rows.length === 0 && emptyMessage}
            <div class="py-6 text-center text-sm">{emptyMessage}</div>
        {/if}
        <Command.Group {heading}>
            {#each rows as row (row.value)}
                <SearchListItem {row} {disabled} />
            {/each}
        </Command.Group>
    </Command.List>
    {#if showBackHint}
        <div
            class="flex items-center gap-1 px-2 py-1.5 text-xs text-muted-foreground"
            data-testid="search-list-back-hint"
        >
            <Kbd>Esc</Kbd> to go back
        </div>
    {/if}
</Command.Root>
