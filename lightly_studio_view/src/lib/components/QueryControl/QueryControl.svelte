<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useQueryPanelState } from '$lib/hooks/useQueryPanelState/useQueryPanelState';

    interface Props {
        collectionId: string;
        onOpen: () => void;
    }
    let { collectionId, onOpen }: Props = $props();

    const { imageQueryExpression, updateQueryExpr } = useImageFilters();

    // Kept per collection outside this component, so a disabled query is still here after
    // switching to the annotations tab and back.
    const { draft, lastQueryExpression } = $derived(useQueryPanelState(collectionId));
    $effect(() => {
        if ($imageQueryExpression?.query_expr_str) {
            lastQueryExpression.set($imageQueryExpression);
        }
    });
</script>

{#if $lastQueryExpression}
    <Segment title="Query">
        <FilterChip
            testId="query-filter-chip"
            checked={!!$imageQueryExpression?.query_expr_str}
            title="Query Filter"
            checkboxLabel={$imageQueryExpression?.query_expr_str
                ? 'Disable query filter'
                : 'Enable query filter'}
            onCheckedChange={(v) => {
                if (v) {
                    updateQueryExpr($lastQueryExpression!);
                } else {
                    updateQueryExpr(undefined);
                }
            }}
            onClear={() => {
                updateQueryExpr(undefined);
                lastQueryExpression.set(null);
                draft.set(null);
            }}
            onclick={onOpen}
        >
            {#snippet subtitle()}
                <div
                    class="truncate font-mono text-xs text-muted-foreground"
                    title={$lastQueryExpression?.query_expr_str}
                >
                    {$lastQueryExpression?.query_expr_str}
                </div>
            {/snippet}
        </FilterChip>
    </Segment>
{/if}
