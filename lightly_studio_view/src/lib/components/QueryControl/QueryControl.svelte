<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import {
        useImageFilters,
        type QueryExpression
    } from '$lib/hooks/useImageFilters/useImageFilters';

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

{#if lastQueryExpression}
    <Segment title="Advanced filters">
        <FilterChip
            testId="query-filter-chip"
            checked={!!$imageQueryExpression?.query_expr_str}
            title="Advanced filters"
            checkboxLabel={$imageQueryExpression?.query_expr_str
                ? 'Disable advanced filters'
                : 'Enable advanced filters'}
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
