<script lang="ts">
    import { Button, Typography } from '$lib/components';
    import { Pencil } from '@lucide/svelte';

    interface Props {
        configuration: Record<string, unknown> | null;
        onEdit?: () => void;
    }
    let { configuration, onEdit }: Props = $props();
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
    <div class="mb-2 flex items-center justify-between gap-2">
        <Typography variant="subtitle2" component="h3">Matching settings</Typography>
        {#if onEdit}
            <Button icon={Pencil} buttonProps={{ size: 'xs', onclick: onEdit }}>Edit</Button>
        {/if}
    </div>
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
