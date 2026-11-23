<script lang="ts">
    import ChartScatter from '@lucide/svelte/icons/chart-scatter';
    import LoaderCircle from '@lucide/svelte/icons/loader-circle';
    import { Button } from '$lib/components/ui/button';
    import { formatDuration } from '$lib/utils';
    import type { PlotComputeView } from '../plotComputeGate';

    interface Props {
        view: Extract<PlotComputeView, 'prompt' | 'computing'>;
        embeddingCount: number;
        /** Singular item name of the collection, for example "image" or "video". */
        itemLabel: string;
        startedAt: number | null;
        onCompute: () => void;
    }

    const TIMER_INTERVAL_MS = 1_000;
    const MS_PER_SECOND = 1_000;

    let { view, embeddingCount, itemLabel, startedAt, onCompute }: Props = $props();

    let now = $state(Date.now());
    $effect(() => {
        if (view !== 'computing') return;
        now = Date.now();
        const interval = setInterval(() => (now = Date.now()), TIMER_INTERVAL_MS);
        return () => clearInterval(interval);
    });

    const elapsed = $derived(formatDuration((now - (startedAt ?? now)) / MS_PER_SECOND));
</script>

<div
    class="flex flex-1 flex-col items-center justify-center gap-2 bg-black px-6 text-center"
    data-testid="plot-compute-prompt"
>
    {#if view === 'prompt'}
        <ChartScatter class="size-8 text-muted-foreground" />
        <div class="text-base font-medium">Plot not computed</div>
        <div class="max-w-64 text-sm text-muted-foreground">
            {embeddingCount.toLocaleString('en-US')}
            {itemLabel}s. The first compute can take several minutes.
        </div>
        <Button class="mt-2" onclick={onCompute}>Compute plot</Button>
    {:else}
        <LoaderCircle class="size-8 animate-spin text-muted-foreground" />
        <div class="text-base font-medium">Computing plot…</div>
        <div class="max-w-64 text-sm text-muted-foreground">
            Running for {elapsed}. The first compute can take several minutes.
        </div>
    {/if}
</div>
