<script lang="ts">
    import X from '@lucide/svelte/icons/x';
    import { Button } from '$lib/components/ui/button';

    interface Props {
        status: 'running' | 'finished' | 'stopped';
        modelId: string;
        total: number;
        done: number;
        annotationCount: number;
        failedCount: number;
        onStop: () => void;
        onViewResults: () => void;
        onClose: () => void;
    }

    let {
        status,
        modelId,
        total,
        done,
        annotationCount,
        failedCount,
        onStop,
        onViewResults,
        onClose
    }: Props = $props();

    const PERCENT = 100;
    const percentDone = $derived(total === 0 ? 0 : (done / total) * PERCENT);
    const title = $derived(
        status === 'running' ? 'Auto-labeling' : status === 'stopped' ? 'Stopped' : 'Done'
    );
</script>

<div
    class="fixed bottom-4 right-4 z-40 flex w-72 flex-col gap-2 rounded-lg border bg-card p-3 text-sm shadow-lg"
    data-testid="auto-label-dock"
>
    <div class="flex items-center justify-between">
        <span class="font-medium">{title} · {modelId}</span>
        {#if status !== 'running'}
            <button aria-label="Close" class="text-muted-foreground" onclick={onClose}>
                <X class="size-4" />
            </button>
        {/if}
    </div>
    <span>{done} of {total} · {annotationCount} annotations</span>
    <div class="h-1.5 rounded-full bg-muted">
        <div class="h-full rounded-full bg-primary" style:width="{percentDone}%"></div>
    </div>
    {#if failedCount > 0}
        <span class="text-xs text-destructive">{failedCount} images failed</span>
    {/if}
    {#if status === 'running'}
        <span class="text-xs text-muted-foreground">Keep this tab open.</span>
        <Button variant="outline" size="sm" onclick={onStop}>Stop</Button>
    {:else}
        <Button size="sm" onclick={onViewResults}>View results</Button>
    {/if}
</div>
