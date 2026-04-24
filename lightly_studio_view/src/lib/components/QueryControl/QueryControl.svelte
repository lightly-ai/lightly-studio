<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Button } from '$lib/components/ui/index.js';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { useFeatureFlags } from '$lib/hooks';
    import {
        useImageFilters,
        type QueryExpression
    } from '$lib/hooks/useImageFilters/useImageFilters';
    import { Filter, Pencil } from '@lucide/svelte';

    interface Props {
        onToggle: () => void;
    }
    let { onToggle }: Props = $props();

    const { featureFlags } = useFeatureFlags();
    const isEnabled = $derived($featureFlags.includes('query_filter'));

    const { imageQueryExpression, updateQueryExpr } = useImageFilters();

    let lastQueryExpression = $state<QueryExpression | null>(null);
    $effect(() => {
        if ($imageQueryExpression?.query_expr_str) {
            lastQueryExpression = $imageQueryExpression;
        }
    });
</script>

{#if isEnabled}
    <Segment title="Query" icon={Filter}>
        {#if lastQueryExpression}
            <div
                class="group flex items-center gap-2 rounded-md border border-border/60 bg-muted/30 p-2 transition-colors hover:bg-muted/50"
            >
                <Checkbox
                    checked={!!$imageQueryExpression?.query_expr_str}
                    onCheckedChange={(v: boolean | 'indeterminate') => {
                        if (v) {
                            updateQueryExpr(lastQueryExpression!);
                        } else {
                            updateQueryExpr(undefined);
                        }
                    }}
                    aria-label={$imageQueryExpression?.query_expr_str
                        ? 'Disable query filter'
                        : 'Enable query filter'}
                />
                <button
                    type="button"
                    class="min-w-0 flex-1 cursor-pointer truncate text-left font-mono text-xs transition-colors {$imageQueryExpression?.query_expr_str
                        ? 'text-foreground'
                        : 'text-muted-foreground'}"
                    onclick={onToggle}
                    title={lastQueryExpression.query_expr_str}
                >
                    {lastQueryExpression.query_expr_str}
                </button>
                <Pencil
                    class="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
                    onclick={onToggle}
                />
            </div>
        {:else}
            <Button
                variant="outline"
                size="sm"
                class="w-full justify-start gap-2 text-muted-foreground"
                onclick={onToggle}
            >
                <Pencil class="h-3.5 w-3.5" />
                <span>Add query filter</span>
            </Button>
        {/if}
    </Segment>
{/if}
