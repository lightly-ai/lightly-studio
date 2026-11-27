<script lang="ts">
    import { cn } from '$lib/utils';
    import { CUBOID_SOURCE_MESSAGES } from '../useCuboidTargetSource';

    interface Props {
        /** The source new cuboids go to. */
        targetSource: string | null;
        /** Whether no source is picked among several. */
        needsPick: boolean;
        /** Why new cuboids cannot be created now. */
        blockedReason: string | null;
    }

    let { targetSource, needsPick, blockedReason }: Props = $props();

    const warning = $derived(
        blockedReason ?? (needsPick || !targetSource ? CUBOID_SOURCE_MESSAGES.pick : null)
    );
</script>

<div
    class={cn(
        'flex items-center gap-2 rounded-full border bg-background/90 px-3 py-1 text-xs shadow-sm',
        warning && 'border-amber-400/60 text-amber-500'
    )}
    data-state={warning ? 'warning' : 'target'}
    data-testid="cuboid-target-chip"
>
    <span class={cn('size-2 rounded-full', warning ? 'bg-amber-400' : 'bg-primary')}></span>
    {#if warning}
        {warning}
    {:else}
        New cuboids go to {targetSource}
    {/if}
</div>
