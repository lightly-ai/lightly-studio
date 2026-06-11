<script lang="ts">
    import { Plus } from '@lucide/svelte';
    import { Portal } from 'bits-ui';
    import { Select, SelectMenuItem } from '$lib/components/Select';
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

    let isOpen = $state(false);
    let hoveredType = $state<StrategyType | null>(null);
    let tooltipRect = $state<DOMRect | null>(null);
    // wrapper element refs used to position the tooltip on keyboard highlight
    let itemRefs: Partial<Record<StrategyType, HTMLElement>> = {};

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

<Select
    icon={Plus}
    triggerLabel="Add strategy"
    class="w-full border border-border"
    testId="add-strategy-button"
    onValueChange={(v) => {
        if (v) onAdd(v as StrategyType);
    }}
    onOpenChange={(open) => {
        isOpen = open;
        if (!open) handleMouseLeave();
    }}
>
    {#snippet children()}
        {#each STRATEGY_OPTIONS as strategy (strategy.type)}
            {@const disabledReason = getDisabledReason(strategy.type)}
            <div
                class="w-full"
                role="none"
                bind:this={itemRefs[strategy.type]}
                onmouseenter={(e) =>
                    handleMouseEnter(strategy.type, e.currentTarget as HTMLElement)}
                onmouseleave={handleMouseLeave}
            >
                <SelectMenuItem
                    value={strategy.type}
                    label={strategy.label}
                    disabled={!!disabledReason}
                    data-testid={`add-strategy-${strategy.type}`}
                    aria-describedby="strategy-desc-{strategy.type}"
                    onHighlight={() => {
                        const el = itemRefs[strategy.type];
                        if (el) handleMouseEnter(strategy.type, el);
                    }}
                    onUnhighlight={() => {
                        // guard against bits-ui firing onUnhighlight after onHighlight of another item
                        if (hoveredType === strategy.type) handleMouseLeave();
                    }}
                />
                <span id="strategy-desc-{strategy.type}" class="sr-only">
                    {strategy.description}{#if disabledReason}: {disabledReason}{/if}
                </span>
            </div>
        {/each}
    {/snippet}
</Select>

{#if isOpen && hoveredType && tooltipRect && hoveredStrategy}
    <Portal>
        <div
            id="strategy-tooltip-{hoveredType}"
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
