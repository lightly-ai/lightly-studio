<script lang="ts">
    import { goto } from '$app/navigation';
    import type { EvaluationRunView } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components';
    import {
        SELECTION_PROBLEM_MESSAGES,
        validateSelection
    } from '$lib/components/EvaluationComparison';
    import { routeHelpers } from '$lib/routes';

    interface Props {
        datasetId: string;
        collectionType: string;
        collectionId: string;
        /** Selected runs, in list order. */
        selectedRuns: EvaluationRunView[];
    }

    const { datasetId, collectionType, collectionId, selectedRuns }: Props = $props();

    const selectionProblem = $derived(validateSelection(selectedRuns));

    const openComparison = () =>
        goto(
            routeHelpers.toEvaluationCompare(
                datasetId,
                collectionType,
                collectionId,
                selectedRuns.map((run) => run.id)
            )
        );
</script>

<Button
    variant="outline"
    buttonProps={{
        size: 'sm',
        disabled: selectionProblem !== null,
        title: selectionProblem ? SELECTION_PROBLEM_MESSAGES[selectionProblem] : undefined,
        onclick: openComparison,
        'data-testid': 'compare-evaluation-runs-button'
    }}>Compare ({selectedRuns.length})</Button
>
