<script lang="ts">
    import type { ClassBalancingParams, StrategyParams } from '$lib/hooks/useStrategyBuilder';
    import AnnotationSource from './AnnotationSource/AnnotationSource.svelte';
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
    <AnnotationSource
        annotationSource={params.annotation_source}
        onUpdate={(source) => onUpdate({ annotation_source: source })}
    />
    <StrengthField
        strength={params.strength}
        id="class-balancing-strength"
        testid="strategy-class-balancing-strength-input"
        onUpdate={(strength) => onUpdate({ strength })}
    />
    {#if params.annotation_source === 'dictionary'}
        <TargetDistribution
            targetDistribution={params.target_distribution}
            {annotationLabels}
            onUpdate={(rows) => onUpdate({ target_distribution: rows })}
        />
    {/if}
</div>
