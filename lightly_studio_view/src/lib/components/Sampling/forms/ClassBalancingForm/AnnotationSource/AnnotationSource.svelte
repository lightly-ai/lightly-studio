<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import * as Select from '$lib/components/ui/select';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import type { ClassBalancingTargetDistributionMode } from '$lib/hooks/useStrategyBuilder';

    interface Props {
        targetDistributionMode: ClassBalancingTargetDistributionMode;
        onUpdate: (mode: ClassBalancingTargetDistributionMode) => void;
    }

    let { targetDistributionMode, onUpdate }: Props = $props();

    const TARGET_DISTRIBUTION_MODE_OPTIONS: {
        value: ClassBalancingTargetDistributionMode;
        label: string;
    }[] = [
        { value: 'uniform', label: 'Uniform' },
        { value: 'input', label: 'Input' },
        { value: 'dictionary', label: 'Dictionary' }
    ];
</script>

<div class="grid gap-2">
    <div class="flex items-center gap-1.5">
        <Label>Target distribution</Label>
        <FieldTooltip content="The target class distribution to optimize toward." />
    </div>
    <Select.Root
        type="single"
        value={targetDistributionMode}
        onValueChange={(value) => onUpdate(value as ClassBalancingTargetDistributionMode)}
    >
        <Select.Trigger class="w-full" data-testid="class-balancing-annotation-source">
            {TARGET_DISTRIBUTION_MODE_OPTIONS.find((o) => o.value === targetDistributionMode)
                ?.label}
        </Select.Trigger>
        <Select.Content>
            <Select.Group>
                {#each TARGET_DISTRIBUTION_MODE_OPTIONS as option (option.value)}
                    <Select.Item
                        value={option.value}
                        label={option.label}
                        data-testid={`class-balancing-annotation-source-${option.value}`}
                    >
                        {option.label}
                    </Select.Item>
                {/each}
            </Select.Group>
        </Select.Content>
    </Select.Root>
</div>
