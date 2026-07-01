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

    // A null gt_label is the false-positive bucket (only a prediction, no ground
    // truth); a null pred_label is the false-negative bucket (only a ground truth, no
    // prediction). Otherwise it is a real class-by-class confusion.
    const chipTitle = $derived.by(() => {
        if (!confusionCell) return '';
        if (confusionCell.gt_label == null) return `Predicted only: ${confusionCell.pred_label}`;
        if (confusionCell.pred_label == null) return `Ground truth only: ${confusionCell.gt_label}`;
        return `GT: ${confusionCell.gt_label} → Pred: ${confusionCell.pred_label}`;
    });

    const clearFilter = () => {
        updateConfusionCell(null);
    };
</script>

{#if confusionCell}
    <Segment title="Confusion Matrix">
        <FilterChip
            checked={true}
            title={chipTitle}
            checkboxLabel="Confusion cell filter"
            testId="confusion-cell-filter-item-chip"
            onCheckedChange={(nextChecked) => {
                if (nextChecked !== true) {
                    clearFilter();
                }
            }}
            onClear={clearFilter}
        />
    </Segment>
{/if}
