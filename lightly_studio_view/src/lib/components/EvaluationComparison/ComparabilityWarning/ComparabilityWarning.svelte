<script lang="ts">
    import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
    import * as Alert from '$lib/components/ui/alert';
    import type { ComparabilityReport } from '../EvaluationComparison.helpers';

    interface Props {
        report: ComparabilityReport;
    }

    const { report }: Props = $props();

    const messages = $derived(
        [
            report.differentGroundTruth && 'Runs use different ground truth annotation sources.',
            report.differentImageSets && 'Runs evaluate different images.',
            report.differentMatchingConfig &&
                'Precision, recall and F1 use different matching settings. mAP is not affected.',
            report.staleRunIds.length > 0 &&
                'Some runs are stale. Their annotations changed after the evaluation.'
        ].filter((message): message is string => typeof message === 'string')
    );
</script>

{#if messages.length > 0}
    <Alert.Root data-testid="comparability-warning">
        <TriangleAlert class="size-4" />
        <Alert.Title>Compare these runs with care</Alert.Title>
        <Alert.Description>
            <ul class="list-disc pl-4">
                {#each messages as message (message)}
                    <li>{message}</li>
                {/each}
            </ul>
        </Alert.Description>
    </Alert.Root>
{/if}
