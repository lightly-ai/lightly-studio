<script lang="ts">
    import { ColorMarker } from '$lib/components/SideMenu';

    interface Props {
        groundTruth: string | null;
        predictions: string | null;
    }

    let { groundTruth, predictions }: Props = $props();
</script>

<span class="mt-2 grid grid-cols-2 gap-2" data-testid="evaluation-run-annotation-sources">
    {#each [{ role: 'Predictions', name: predictions, testId: 'evaluation-run-prediction-annotation-source' }, { role: 'Ground truth', name: groundTruth, testId: 'evaluation-run-gt-annotation-source' }] as source (source.role)}
        <span
            class="flex min-w-0 flex-col gap-0.5 rounded-md border border-border bg-muted/40 px-2 py-1"
        >
            <span class="text-xs text-muted-foreground">{source.role}</span>
            <span
                class="flex min-w-0 items-center gap-2 text-sm font-medium"
                data-testid={source.testId}
            >
                {#if source.name}<ColorMarker label={source.name} />{/if}
                <span class="min-w-0 break-words">{source.name ?? 'Unknown'}</span>
            </span>
        </span>
    {/each}
</span>
