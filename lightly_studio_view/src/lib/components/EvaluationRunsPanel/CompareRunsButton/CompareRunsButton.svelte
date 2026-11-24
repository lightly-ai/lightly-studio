<script lang="ts">
    import type { EvaluationRunView } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components';
    import {
        SELECTION_PROBLEM_MESSAGES,
        validateSelection
    } from '$lib/components/EvaluationComparison';

    interface Props {
        /** Selected runs, in list order. */
        selectedRuns: EvaluationRunView[];
        onCompare: (runIds: string[]) => void;
    }

    const { selectedRuns, onCompare }: Props = $props();

    const selectionProblem = $derived(validateSelection(selectedRuns));
</script>

<Button
    variant="outline"
    buttonProps={{
        size: 'sm',
        disabled: selectionProblem !== null,
        title: selectionProblem ? SELECTION_PROBLEM_MESSAGES[selectionProblem] : undefined,
        onclick: () => onCompare(selectedRuns.map((run) => run.id)),
        'data-testid': 'compare-evaluation-runs-button'
    }}>Compare ({selectedRuns.length})</Button
>
