<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import type { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    type QueryExpression = Parameters<ReturnType<typeof useImageFilters>['updateQueryExpr']>[0];

    interface Props {
        onOpen: () => void;
        queryExpression: QueryExpression | null;
        updateQueryExpr: ReturnType<typeof useImageFilters>['updateQueryExpr'];
    }
    let { onOpen, queryExpression, updateQueryExpr }: Props = $props();

    let lastQueryExpression = $state<QueryExpression | null>(null);
    $effect(() => {
        if (queryExpression?.query_expr_str) {
            lastQueryExpression = queryExpression;
        }
    });
</script>

{#if lastQueryExpression}
    <Segment title="Query">
        <FilterChip
            testId="query-filter-chip"
            checked={!!queryExpression?.query_expr_str}
            title="Query Filter"
            checkboxLabel={queryExpression?.query_expr_str
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
    </Segment>
{/if}
