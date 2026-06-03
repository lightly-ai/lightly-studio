<script lang="ts">
    import type { ClassBalancingParams, StrategyParams } from '$lib/hooks/useStrategyBuilder';
    import TargetDistributionModeSelect from './TargetDistributionModeSelect/TargetDistributionModeSelect.svelte';
    import StrengthField from '$lib/components/Sampling/forms/StrengthField/StrengthField.svelte';
    import TargetDistribution from './TargetDistribution/TargetDistribution.svelte';

    interface Props {
        params: ClassBalancingParams;
        annotationLabels: string[];
        onUpdate: (params: Partial<StrategyParams>) => void;
    }

    let { params, annotationLabels, onUpdate }: Props = $props();
</script>

<div class="grid gap-3" data-testid="class-balancing-form">
    <TargetDistributionModeSelect
        targetDistributionMode={params.target_distribution_mode}
        onUpdate={(mode) => onUpdate({ target_distribution_mode: mode })}
    />
    <StrengthField
        strength={params.strength}
        id="class-balancing-strength"
        testid="strategy-class-balancing-strength-input"
        onUpdate={(strength) => onUpdate({ strength })}
    />
    {#if params.target_distribution_mode === 'dictionary'}
        <TargetDistribution
            targetDistribution={params.target_distribution}
            {annotationLabels}
            onUpdate={(rows) => onUpdate({ target_distribution: rows })}
        />
    {/if}
</div>
