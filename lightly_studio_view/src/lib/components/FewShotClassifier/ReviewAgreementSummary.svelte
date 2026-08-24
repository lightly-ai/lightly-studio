<script lang="ts">
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { Info } from '@lucide/svelte';
    import { formatAgreement } from './reviewAgreement';

    interface Props {
        confirmedPredictions: number;
        reviewedSamples: number;
        latestConfirmedPredictions: number | null;
        latestReviewedSamples: number | null;
    }

    const {
        confirmedPredictions,
        reviewedSamples,
        latestConfirmedPredictions,
        latestReviewedSamples
    }: Props = $props();
</script>

<section class="rounded-lg border bg-muted/20 p-3 text-sm" aria-label="Review agreement">
    <div class="flex items-center gap-2 font-medium">
        Review agreement
        <Tooltip
            content="Agreement measures how often your corrections confirm predictions on balanced review samples. It is not whole-dataset accuracy."
        >
            <Info class="size-4 text-muted-foreground" aria-label="About review agreement" />
        </Tooltip>
    </div>
    {#if latestReviewedSamples === null}
        <p class="mt-1 text-muted-foreground">Review a batch to estimate agreement.</p>
    {:else}
        <div class="mt-1 flex flex-wrap gap-x-5 gap-y-1 text-muted-foreground">
            <span
                >Overall review agreement: {formatAgreement(
                    confirmedPredictions,
                    reviewedSamples
                )}</span
            >
            <span
                >Latest-round agreement: {formatAgreement(
                    latestConfirmedPredictions ?? 0,
                    latestReviewedSamples
                )}</span
            >
            <span>{confirmedPredictions} of {reviewedSamples} predictions confirmed</span>
        </div>
    {/if}
</section>
