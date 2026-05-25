<script lang="ts">
    import { Plus } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import { cn } from '$lib/utils';
    import { STRATEGY_OPTIONS, type StrategyType } from '../useStrategyBuilder/useStrategyBuilder';

    interface Props {
        isSimilarityDisabled?: boolean;
        isMetadataWeightingDisabled?: boolean;
        isClassBalancingDisabled?: boolean;
        onAdd: (type: StrategyType) => void;
    }

    let {
        isSimilarityDisabled = false,
        isMetadataWeightingDisabled = false,
        isClassBalancingDisabled = false,
        onAdd
    }: Props = $props();
    let open = $state(false);

    function isDisabled(type: StrategyType): boolean {
        if (type === 'similarity') return isSimilarityDisabled;
        if (type === 'metadata_weighting') return isMetadataWeightingDisabled;
        if (type === 'class_balancing') return isClassBalancingDisabled;
        return false;
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
                <button
                    type="button"
                    class={cn(
                        'rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent hover:text-accent-foreground',
                        isDisabled(strategy.type) && 'cursor-not-allowed opacity-50'
                    )}
                    disabled={isDisabled(strategy.type)}
                    onclick={() => {
                        onAdd(strategy.type);
                        open = false;
                    }}
                    data-testid={`add-strategy-${strategy.type}`}
                >
                    {strategy.label}
                </button>
            {/each}
        </div>
    </Popover.Content>
</Popover.Root>
