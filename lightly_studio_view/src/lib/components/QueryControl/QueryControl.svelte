<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Button } from '$lib/components/ui/index.js';
    import {
        useImageFilters,
        type QueryExpression
    } from '$lib/hooks/useImageFilters/useImageFilters';
    import { Pencil } from '@lucide/svelte';

    interface Props {
        onOpen: () => void;
    }
    let { onOpen }: Props = $props();

    const { imageQueryExpression, updateQueryExpr } = useImageFilters();

    let lastQueryExpression = $state<QueryExpression | null>(null);
    $effect(() => {
        if ($imageQueryExpression?.query_expr_str) {
            lastQueryExpression = $imageQueryExpression;
        }
    });
</script>

<Segment title="Query">
    {#if lastQueryExpression}
        <FilterChip
            testId="query-filter-chip"
            checked={!!$imageQueryExpression?.query_expr_str}
            title="Query Filter"
            checkboxLabel={$imageQueryExpression?.query_expr_str
                ? 'Disable query filter'
                : 'Enable query filter'}
            onCheckedChange={(v) => {
                if (v) {
                    updateQueryExpr(lastQueryExpression!);
                } else {
                    updateQueryExpr(undefined);
                }
            }}
            onClear={() => {
                updateQueryExpr(undefined);
                lastQueryExpression = null;
            }}
            onclick={onOpen}
        >
            {#snippet subtitle()}
                <div
                    class="truncate font-mono text-xs text-muted-foreground"
                    title={lastQueryExpression?.query_expr_str}
                >
                    {lastQueryExpression?.query_expr_str}
                </div>
            {/snippet}
        </FilterChip>
    {:else}
        <Button
            variant="outline"
            size="sm"
            class="w-full justify-start gap-2 text-muted-foreground"
            data-testid="query-filter-add-button"
            onclick={onOpen}
        >
            <Pencil class="h-3.5 w-3.5" />
            <span>Add query filter</span>
        </Button>
    {/if}
</Segment>
