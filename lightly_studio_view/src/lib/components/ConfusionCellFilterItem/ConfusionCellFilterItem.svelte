<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';

    const { filterParams, updateConfusionCell } = useImageFilters();

    // The selected cell lives in the shared, module-level filter store, so this chip
    // stays in sync with clicks coming from the confusion matrix panel.
    const confusionCell = $derived(
        $filterParams?.mode === 'normal' ? ($filterParams.filters?.confusion_cell ?? null) : null
    );

    const clearFilter = () => {
        updateConfusionCell(null);
    };
</script>

{#if confusionCell}
    <Segment title="Confusion Matrix">
        <FilterChip
            checked={true}
            title="Confusion matrix filter"
            checkboxLabel="Confusion cell filter"
            testId="confusion-cell-filter-item-chip"
            onCheckedChange={(nextChecked) => {
                if (nextChecked !== true) clearFilter();
            }}
            onClear={clearFilter}
        >
            {#snippet content()}
                <dl
                    class="grid min-w-0 flex-1 grid-cols-[max-content_minmax(0,1fr)] items-baseline gap-x-2 gap-y-1 text-sm"
                >
                    {#each [{ role: 'Ground truth', value: confusionCell.gt_label, missing: 'No ground truth' }, { role: 'Prediction', value: confusionCell.pred_label, missing: 'No prediction' }] as field (field.role)}
                        <dt class="text-xs text-muted-foreground">{field.role}</dt>
                        <dd class="[overflow-wrap:anywhere]">
                            {#if field.value == null}
                                <em class="text-muted-foreground">{field.missing}</em>
                            {:else}
                                <span class="font-medium">{field.value}</span>
                            {/if}
                        </dd>
                    {/each}
                </dl>
            {/snippet}
        </FilterChip>
    </Segment>
{/if}
