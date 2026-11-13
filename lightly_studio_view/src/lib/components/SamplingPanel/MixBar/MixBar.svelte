<script lang="ts">
    import { STRATEGY_LABELS, type StrategyInstance } from '$lib/hooks/useStrategyBuilder';

    interface Props {
        instances: StrategyInstance[];
    }

    let { instances }: Props = $props();

    const SEGMENT_COLORS = [
        'bg-primary',
        'bg-emerald-500',
        'bg-amber-500',
        'bg-sky-500',
        'bg-fuchsia-500'
    ];

    // A negative strength inverts a strategy, so its size in the mix is its magnitude.
    const total = $derived(
        instances.reduce((sum, instance) => sum + Math.abs(instance.params.strength), 0)
    );

    function sharePercent(instance: StrategyInstance): number {
        if (total <= 0) return 0;
        return Math.round((Math.abs(instance.params.strength) / total) * 100);
    }
</script>

<div class="grid gap-2" data-testid="sampling-mix-bar">
    <div class="flex h-2 w-full overflow-hidden rounded-full bg-muted">
        {#each instances as instance, index (instance.id)}
            <div
                class="h-full {SEGMENT_COLORS[index % SEGMENT_COLORS.length]}"
                style="width: {sharePercent(instance)}%"
            ></div>
        {/each}
    </div>
    <div class="flex flex-wrap gap-x-3 gap-y-1">
        {#each instances as instance, index (instance.id)}
            <span class="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span
                    class="size-2 shrink-0 rounded-full {SEGMENT_COLORS[
                        index % SEGMENT_COLORS.length
                    ]}"
                ></span>
                {STRATEGY_LABELS[instance.type]}
                {sharePercent(instance)}%
                {#if instance.params.strength < 0}· prefer low{/if}
            </span>
        {/each}
    </div>
</div>
