<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { MATCH_FILTER_NAV, parseConfusionCellParam, setConfusionCellInUrl } from '$lib/utils';

    // The cell lives in the URL, so this chip stays in sync with clicks coming from
    // the confusion matrix panel. Parsing with the route's run id inherently scopes it
    // to the run this matches view is showing.
    const confusionCell = $derived(
        parseConfusionCellParam(page.url.searchParams, page.params.evaluation_run_id ?? '') ?? null
    );

    const clear = () => goto(setConfusionCellInUrl(page.url, null), MATCH_FILTER_NAV);

    // A null gt_label is the false-positive bucket (only a prediction, no ground
    // truth); a null pred_label is the false-negative bucket (only a ground truth, no
    // prediction). Otherwise it is a real class-by-class confusion.
    const chipTitle = $derived.by(() => {
        if (!confusionCell) return '';
        if (confusionCell.gt_label == null) return `Predicted only: ${confusionCell.pred_label}`;
        if (confusionCell.pred_label == null) return `Ground truth only: ${confusionCell.gt_label}`;
        return `GT: ${confusionCell.gt_label} → Pred: ${confusionCell.pred_label}`;
    });
</script>

{#if confusionCell}
    <Segment title="Confusion Matrix">
        <FilterChip
            checked={true}
            title={chipTitle}
            checkboxLabel="Confusion cell filter"
            testId="match-confusion-cell-filter-item-chip"
            onCheckedChange={(nextChecked) => {
                if (nextChecked !== true) {
                    clear();
                }
            }}
            onClear={clear}
        />
    </Segment>
{/if}
