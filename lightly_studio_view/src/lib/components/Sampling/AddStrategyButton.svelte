<script lang="ts">
    import { Plus } from '@lucide/svelte';
    import { Portal } from 'bits-ui';
    import * as Select from '$lib/components/ui/select';
    import { STRATEGY_OPTIONS, type StrategyType } from '$lib/hooks/useStrategyBuilder';

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

    let hoveredType = $state<StrategyType | null>(null);
    let tooltipRect = $state<DOMRect | null>(null);

    function getDisabledReason(type: StrategyType): string | undefined {
        if (type === 'similarity') return similarityDisabledReason;
        if (type === 'metadata_weighting') return metadataWeightingDisabledReason;
        if (type === 'class_balancing') return classBalancingDisabledReason;
        return undefined;
    }

    function handleMouseEnter(type: StrategyType, el: HTMLElement) {
        hoveredType = type;
        tooltipRect = el.getBoundingClientRect();
    }

    function handleMouseLeave() {
        hoveredType = null;
        tooltipRect = null;
    }

    const hoveredStrategy = $derived(
        hoveredType ? STRATEGY_OPTIONS.find((s) => s.type === hoveredType) : null
    );
    const hoveredDisabledReason = $derived(
        hoveredType ? getDisabledReason(hoveredType) : undefined
    );
</script>

<Select.Root
    type="single"
    onValueChange={(v) => {
        if (v) onAdd(v as StrategyType);
    }}
    onOpenChange={(open) => {
        if (!open) handleMouseLeave();
    }}
>
    <Select.Trigger class="w-full" data-testid="add-strategy-button">
        <Plus class="mr-2 size-4" />
        Add strategy
    </Select.Trigger>
    <Select.Content>
        {#each STRATEGY_OPTIONS as strategy (strategy.type)}
            <div
                class="w-full"
                role="none"
                onmouseenter={(e) =>
                    handleMouseEnter(strategy.type, e.currentTarget as HTMLElement)}
                onmouseleave={handleMouseLeave}
            >
                <Select.Item
                    value={strategy.type}
                    label={strategy.label}
                    disabled={!!getDisabledReason(strategy.type)}
                    data-testid={`add-strategy-${strategy.type}`}
                />
            </div>
        {/each}
    </Select.Content>
</Select.Root>

{#if hoveredType && tooltipRect && hoveredStrategy}
    <Portal>
        <div
            role="tooltip"
            style="position: fixed; left: {tooltipRect.right + 8}px; top: {tooltipRect.top +
                tooltipRect.height / 2}px; transform: translateY(-50%);"
            class="z-[9999] w-max max-w-[200px] rounded-md bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md"
        >
            <p>{hoveredStrategy.description}</p>
            {#if hoveredDisabledReason}
                <p class="mt-1.5 border-t border-border pt-1.5 text-destructive">
                    {hoveredDisabledReason}
                </p>
            {/if}
        </div>
    </Portal>
{/if}
