<script lang="ts">
    import { Typography } from '$lib/components';

    interface Props {
        configuration: Record<string, unknown> | null;
    }
    let { configuration }: Props = $props();
    const entries = $derived(Object.entries(configuration ?? {}));
    const labels: Record<string, string> = {
        iou_threshold: 'Minimum overlap (IoU)',
        classwise: 'Class matching'
    };
    const formatValue = (key: string, value: unknown): string => {
        if (key === 'classwise' && typeof value === 'boolean') {
            return value ? 'Same class only' : 'Any class';
        }
        if (key === 'iou_threshold' && typeof value === 'number') return value.toFixed(2);
        if (value === null || value === undefined) return '—';
        return typeof value === 'object' ? JSON.stringify(value) : String(value);
    };
</script>

<section>
    <Typography variant="subtitle2" component="h3" className="mb-2">Matching settings</Typography>
    {#if entries.length === 0}
        <Typography variant="body2" className="text-muted-foreground"
            >No configuration recorded.</Typography
        >
    {:else}
        <dl
            class="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-2"
            data-testid="evaluation-run-config"
        >
            {#each entries as [key, value] (key)}
                <dt class="text-sm text-muted-foreground">{labels[key] ?? key}</dt>
                <dd class="break-words text-right text-sm">{formatValue(key, value)}</dd>
            {/each}
        </dl>
        {#if typeof configuration?.iou_threshold === 'number'}
            <p class="mt-2 text-xs text-muted-foreground">
                Higher IoU requires a closer overlap to count as a match.
            </p>
        {/if}
    {/if}
</section>
