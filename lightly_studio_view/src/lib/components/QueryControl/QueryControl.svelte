<script lang="ts">
    import { Button } from '$lib/components';
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import Tooltip from '$lib/components/ui/tooltip/tooltip.svelte';
    import {
        useImageFilters,
        type QueryExpression
    } from '$lib/hooks/useImageFilters/useImageFilters';
    import { ListFilterPlus } from '@lucide/svelte';

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

<Segment title="Advanced filters">
    {#if lastQueryExpression}
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
    {:else}
        <Tooltip
            content="Write a query to filter with conditions the simple filters can't express: e.g. images that contain both a cat AND a dog. Combine annotation classes, image properties, and tags with AND, OR, and NOT."
            position="right"
            triggerClass="block w-full"
        >
            <Button
                icon={ListFilterPlus}
                variant="outline"
                buttonProps={{
                    onclick: onOpen,
                    'data-testid': 'query-filter-add-button',
                    class: 'w-full'
                }}
            >
                Create advanced filters
            </Button>
        </Tooltip>
    {/if}
</Segment>