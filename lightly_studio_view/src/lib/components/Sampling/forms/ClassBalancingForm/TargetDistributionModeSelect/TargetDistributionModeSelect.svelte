<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import { Select } from '$lib/components/Select';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import type { ClassBalancingTargetDistributionMode } from '$lib/hooks/useStrategyBuilder';

    interface Props {
        targetDistributionMode: ClassBalancingTargetDistributionMode;
        onUpdate: (mode: ClassBalancingTargetDistributionMode) => void;
    }

    let { targetDistributionMode, onUpdate }: Props = $props();

    const items = [
        {
            value: 'uniform',
            label: 'Uniform',
            testId: 'class-balancing-target-distribution-uniform'
        },
        { value: 'input', label: 'Input', testId: 'class-balancing-target-distribution-input' },
        {
            value: 'dictionary',
            label: 'Dictionary',
            testId: 'class-balancing-target-distribution-dictionary'
        }
    ] satisfies { value: ClassBalancingTargetDistributionMode; label: string; testId: string }[];
</script>

<div class="grid gap-2">
    <div class="flex items-center gap-1.5">
        <Label>Target distribution</Label>
        <FieldTooltip content="The target class distribution to optimize toward." />
    </div>
    <Select
        {items}
        value={targetDistributionMode}
        class="w-full"
        testId="class-balancing-target-distribution"
        onValueChange={(value) => onUpdate(value as ClassBalancingTargetDistributionMode)}
    />
</div>
