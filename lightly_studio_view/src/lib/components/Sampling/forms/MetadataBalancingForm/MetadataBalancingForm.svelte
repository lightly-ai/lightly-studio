<script lang="ts">
    import type { MetadataBalancingParams, StrategyParams } from '$lib/hooks/useStrategyBuilder';
    import TargetDistributionModeSelect from '../ClassBalancingForm/TargetDistributionModeSelect/TargetDistributionModeSelect.svelte';
    import TargetDistribution from '../ClassBalancingForm/TargetDistribution/TargetDistribution.svelte';
    import MetadataKeySelect from '../MetadataWeightingForm/MetadataKeySelect.svelte';
    import StrengthField from '$lib/components/Sampling/forms/StrengthField/StrengthField.svelte';
    import { Label } from '$lib/components/ui/label';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';

    interface Props {
        instanceId: string;
        params: MetadataBalancingParams;
        metadataFieldNames?: string[];
        metadataValuesByKey?: Record<string, string[]>;
        onUpdate: (params: Partial<StrategyParams>) => void;
    }

    let {
        instanceId,
        params,
        metadataFieldNames = [],
        metadataValuesByKey = {},
        onUpdate
    }: Props = $props();

    const testIdPrefix = $derived(`metadata-balancing-${instanceId}`);
    const values = $derived(metadataValuesByKey[params.metadata_key] ?? []);
</script>

<div class="grid gap-3" data-testid="metadata-balancing-form">
    <div class="grid gap-2">
        <div class="flex items-center gap-1.5">
            <Label>Metadata Key</Label>
            <FieldTooltip
                content="A categorical metadata field (string or boolean) on this collection. Balancing shifts the selection toward the target distribution over this field's values."
            />
        </div>
        {#if metadataFieldNames.length > 0}
            <MetadataKeySelect
                value={params.metadata_key}
                fieldNames={metadataFieldNames}
                testId={`${testIdPrefix}-key`}
                onValueChange={(value) => onUpdate({ metadata_key: value })}
            />
        {/if}
    </div>
    <TargetDistributionModeSelect
        targetDistributionMode={params.target_distribution_mode}
        {testIdPrefix}
        onUpdate={(mode) => onUpdate({ target_distribution_mode: mode })}
    />
    <StrengthField
        strength={params.strength}
        id={`metadata-balancing-strength-${instanceId}`}
        testid={`strategy-metadata-balancing-strength-input-${instanceId}`}
        min={0}
        onUpdate={(strength) => onUpdate({ strength })}
    />
    {#if params.target_distribution_mode === 'dictionary'}
        <TargetDistribution
            targetDistribution={params.target_distribution}
            annotationLabels={values}
            {testIdPrefix}
            onUpdate={(rows) => onUpdate({ target_distribution: rows })}
        />
    {/if}
</div>
