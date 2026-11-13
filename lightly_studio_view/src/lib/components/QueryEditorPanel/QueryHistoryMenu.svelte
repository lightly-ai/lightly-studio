<script lang="ts">
    import { History } from '@lucide/svelte';
    import * as Popover from '$lib/components/ui/popover';

    interface Props {
        /** Applied queries, newest first. */
        queries: string[];
        onSelect: (query: string) => void;
    }

    const { queries, onSelect }: Props = $props();

    let open = $state(false);

    const selectQuery = (query: string) => {
        open = false;
        onSelect(query);
    };
</script>

<Popover.Root bind:open>
    <Popover.Trigger
        class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground"
        aria-label="Query history"
        title="Query history"
        data-testid="query-history-button"
    >
        <History class="size-4" />
    </Popover.Trigger>
    <Popover.Content
        class="scrollbar-thin max-h-80 w-96 overflow-y-auto overscroll-contain p-1"
        align="end"
    >
        {#each queries as query (query)}
            <button
                type="button"
                class="w-full whitespace-pre-wrap break-words rounded-sm px-2 py-1.5 text-left font-mono text-xs text-foreground hover:bg-accent"
                data-testid="query-history-item"
                onclick={() => selectQuery(query)}
            >
                {query}
            </button>
        {:else}
            <p class="px-2 py-1.5 text-sm text-muted-foreground">No previous queries</p>
        {/each}
    </Popover.Content>
</Popover.Root>
