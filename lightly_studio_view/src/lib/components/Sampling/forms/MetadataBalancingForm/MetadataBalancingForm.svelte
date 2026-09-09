<script lang="ts">
    import type { StrategyInstance, StrategyParams } from '$lib/hooks/useStrategyBuilder';
    import TargetDistributionModeSelect from '$lib/components/Sampling/forms/TargetDistributionModeSelect/TargetDistributionModeSelect.svelte';
    import TargetDistribution from '$lib/components/Sampling/forms/TargetDistribution/TargetDistribution.svelte';
    import MetadataKeySelect from '../MetadataWeightingForm/MetadataKeySelect.svelte';
    import StrengthField from '$lib/components/Sampling/forms/StrengthField/StrengthField.svelte';
    import { Label } from '$lib/components/ui/label';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';

    type MetadataBalancingParams = Extract<
        StrategyInstance,
        { type: 'metadata_balancing' }
    >['params'];

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

    function selectMetadataKey(metadataKey: string) {
        if (metadataKey === params.metadata_key) {
            return;
        }
        // The rows hold values of the previously selected field, so they no longer apply.
        onUpdate({ metadata_key: metadataKey, target_distribution: [] });
    }
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
                onValueChange={selectMetadataKey}
            />
        {/if}
    </div>
    <TargetDistributionModeSelect
        targetDistributionMode={params.target_distribution_mode}
        {testIdPrefix}
        tooltipContent="The target distribution over the metadata field's values to optimize toward."
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
            options={values}
            {testIdPrefix}
            itemLabel="metadata value"
            tooltipExample="sunny: 0.3, rainy: 0.7"
            onUpdate={(rows) => onUpdate({ target_distribution: rows })}
        />
    {/if}
</div>
