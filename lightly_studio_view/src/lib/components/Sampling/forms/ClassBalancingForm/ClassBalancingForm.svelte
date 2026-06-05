<script lang="ts">
    import type { ClassBalancingParams, StrategyParams } from '$lib/hooks/useStrategyBuilder';
    import TargetDistributionModeSelect from './TargetDistributionModeSelect/TargetDistributionModeSelect.svelte';
    import StrengthField from '$lib/components/Sampling/forms/StrengthField/StrengthField.svelte';
    import TargetDistribution from './TargetDistribution/TargetDistribution.svelte';
    import AnnotationSourceSelect from '$lib/components/AnnotationSourceSelect/AnnotationSourceSelect.svelte';
    import { Label } from '$lib/components/ui/label';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';

    interface Props {
        params: ClassBalancingParams;
        annotationLabels: string[];
        annotationSourceOptions?: { id: string; name: string }[];
        onUpdate: (params: Partial<StrategyParams>) => void;
    }

    let { params, annotationLabels, annotationSourceOptions = [], onUpdate }: Props = $props();
</script>

<div class="grid gap-3" data-testid="class-balancing-form">
    <div class="grid gap-2">
        <div class="flex items-center gap-1.5">
            <Label for="class-balancing-annotation-source">Annotation Source</Label>
            <FieldTooltip
                content="The annotation collection used to read class labels for balancing."
            />
        </div>
        <AnnotationSourceSelect
            id="class-balancing-annotation-source"
            sourceOptions={annotationSourceOptions}
            selectedSource={params.annotation_source_id}
            onSelect={(id) => onUpdate({ annotation_source_id: id })}
        />
    </div>
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
