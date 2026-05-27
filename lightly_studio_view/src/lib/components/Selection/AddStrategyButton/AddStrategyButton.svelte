<script lang="ts">
    import { Plus } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import { cn } from '$lib/utils';
    import { STRATEGY_OPTIONS, type StrategyType } from '../useStrategyBuilder/useStrategyBuilder';

    interface Props {
        similarityDisabledReason?: string;
        metadataWeightingDisabledReason?: string;
        classBalancingDisabledReason?: string;
        onAdd: (type: StrategyType) => void;
    }

    let {
        similarityDisabledReason,
        metadataWeightingDisabledReason,
        classBalancingDisabledReason,
        onAdd
    }: Props = $props();
    let open = $state(false);
    let hoveredType = $state<StrategyType | null>(null);

    function getDisabledReason(type: StrategyType): string | undefined {
        if (type === 'similarity') return similarityDisabledReason;
        if (type === 'metadata_weighting') return metadataWeightingDisabledReason;
        if (type === 'class_balancing') return classBalancingDisabledReason;
        return undefined;
    }
</script>

<Popover.Root bind:open>
    <Popover.Trigger class="w-full">
        <Button variant="outline" class="w-full" data-testid="add-strategy-button">
            <Plus class="size-4" />
            Add strategy
        </Button>
    </Popover.Trigger>
    <Popover.Content class="w-56 p-1" align="start">
        <div class="flex flex-col gap-1">
            {#each STRATEGY_OPTIONS as strategy (strategy.type)}
                {@const disabledReason = getDisabledReason(strategy.type)}
                <div
                    class="relative w-full"
                    onmouseenter={() => (hoveredType = strategy.type)}
                    onmouseleave={() => (hoveredType = null)}
                >
                    {#if disabledReason}
                        <button
                            type="button"
                            class={cn(
                                'w-full rounded-sm px-2 py-1.5 text-left text-sm cursor-not-allowed opacity-50'
                            )}
                            disabled
                            data-testid={`add-strategy-${strategy.type}`}
                        >
                            {strategy.label}
                        </button>
                    {:else}
                        <button
                            type="button"
                            class="w-full rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent hover:text-accent-foreground"
                            onclick={() => {
                                onAdd(strategy.type);
                                open = false;
                            }}
                            data-testid={`add-strategy-${strategy.type}`}
                        >
                            {strategy.label}
                        </button>
                    {/if}
                    {#if hoveredType === strategy.type}
                        <div
                            class="absolute left-full top-1/2 z-[9999] ml-2 w-max max-w-[200px] -translate-y-1/2 rounded-md bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md"
                            role="tooltip"
                        >
                            <p>{strategy.description}</p>
                            {#if disabledReason}
                                <p class="mt-1.5 border-t border-border pt-1.5 text-destructive">{disabledReason}</p>
                            {/if}
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    </Popover.Content>
</Popover.Root>
