<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import { Select } from '$lib/components/Select';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import type { ClassBalancingTargetDistributionMode } from '$lib/hooks/useStrategyBuilder';

    interface Props {
        targetDistributionMode: ClassBalancingTargetDistributionMode;
        onUpdate: (mode: ClassBalancingTargetDistributionMode) => void;
        testIdPrefix?: string;
        tooltipContent?: string;
    }

    let {
        targetDistributionMode,
        onUpdate,
        testIdPrefix = 'class-balancing',
        tooltipContent = 'The target annotation class distribution to optimize toward.'
    }: Props = $props();

    const items = $derived([
        {
            value: 'uniform',
            label: 'Uniform',
            testId: `${testIdPrefix}-target-distribution-uniform`
        },
        { value: 'input', label: 'Input', testId: `${testIdPrefix}-target-distribution-input` },
        {
            value: 'dictionary',
            label: 'Dictionary',
            testId: `${testIdPrefix}-target-distribution-dictionary`
        }
    ] satisfies { value: ClassBalancingTargetDistributionMode; label: string; testId: string }[]);
</script>

<div class="grid gap-2">
    <div class="flex items-center gap-1.5">
        <Label>Target distribution</Label>
        <FieldTooltip content={tooltipContent} />
    </div>
    <Select
        {items}
        value={targetDistributionMode}
        class="w-full"
        testId={`${testIdPrefix}-target-distribution`}
        onValueChange={(value) => onUpdate(value as ClassBalancingTargetDistributionMode)}
    />
</div>
