<script lang="ts">
    import { Button } from '$lib/components';
    import { useRecomputeEvaluationRun } from '$lib/hooks';

    interface Props {
        /** The dataset the evaluation run belongs to. */
        datasetId: string;
        /** The evaluation run to recompute. */
        runId: string;
    }

    const { datasetId, runId }: Props = $props();

    const { mutation, recompute } = useRecomputeEvaluationRun(() => ({ datasetId, runId }));
</script>

<section data-testid="evaluation-run-stale-section">
    <p class="mb-2 text-sm text-muted-foreground">
        Annotations in the evaluated annotation sources were modified after this evaluation was run.
        Recomputing will update results using the current input and annotations, which may differ
        from the original run.
    </p>
    <Button
        variant="outline"
        isPending={mutation.isPending}
        buttonProps={{
            type: 'button',
            disabled: mutation.isPending,
            onclick: recompute,
            class: 'w-full',
            'data-testid': 'evaluation-run-recompute-button'
        }}
    >
        {mutation.isPending ? 'Recomputing…' : 'Recompute'}
    </Button>
</section>
