<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { derived } from 'svelte/store';

    const { filterParams, updateConfusionCell } = useImageFilters();

    // The selected cell lives in the shared, module-level filter store, so this chip
    // stays in sync with clicks coming from the confusion matrix panel.
    const confusionCell = derived(filterParams, ($filterParams) =>
        $filterParams?.mode === 'normal' ? ($filterParams.filters?.confusion_cell ?? null) : null
    );

    const clearFilter = () => {
        updateConfusionCell(null);
    };
</script>

{#if $confusionCell}
    <Segment title="Confusion Matrix">
        <FilterChip
            checked={true}
            title={`Confused: ${$confusionCell.gt_label} → ${$confusionCell.pred_label}`}
            checkboxLabel="Confusion cell filter"
            testId="confusion-cell-filter-chip"
            onCheckedChange={(nextChecked) => {
                if (nextChecked !== true) {
                    clearFilter();
                }
            }}
            onClear={clearFilter}
        />
    </Segment>
{/if}
