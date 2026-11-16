<script lang="ts">
    import History from '@lucide/svelte/icons/history';
    import { Button } from '$lib/components';
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
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                variant="outline"
                icon={History}
                ariaLabel="Query history"
                buttonProps={{ ...props, 'data-testid': 'query-history-button' }}
            >
                History
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content
        class="scrollbar-thin max-h-80 w-96 overflow-y-auto overscroll-contain p-1"
        side="top"
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
