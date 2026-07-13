<script lang="ts">
    import type {
        MetadataClassBalancingParams,
        StrategyParams
    } from '$lib/hooks/useStrategyBuilder';
    import TargetDistributionModeSelect from '../ClassBalancingForm/TargetDistributionModeSelect/TargetDistributionModeSelect.svelte';
    import TargetDistribution from '../ClassBalancingForm/TargetDistribution/TargetDistribution.svelte';
    import StrengthField from '$lib/components/Sampling/forms/StrengthField/StrengthField.svelte';
    import MetadataKeySelect from '../MetadataWeightingForm/MetadataKeySelect.svelte';
    import { Label } from '$lib/components/ui/label';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';

    interface Props {
        instanceId: string;
        params: MetadataClassBalancingParams;
        metadataFieldNames: string[];
        metadataCategoricalValues?: Record<string, string[]>;
        onUpdate: (params: Partial<StrategyParams>) => void;
    }

    let {
        instanceId,
        params,
        metadataFieldNames,
        metadataCategoricalValues = {},
        onUpdate
    }: Props = $props();

    const distinctValues = $derived(metadataCategoricalValues[params.metadata_key] ?? []);
</script>

<div class="grid gap-3" data-testid="metadata-class-balancing-form">
    <div class="grid gap-2">
        <div class="flex items-center gap-1.5">
            <Label for={`metadata-class-balancing-key-${instanceId}`}>Metadata Key</Label>
            <FieldTooltip
                content="A categorical metadata field (string or boolean) indexed on this collection. Balancing shifts the selection toward the target distribution over this key's values."
            />
        </div>
        {#if metadataFieldNames.length > 0}
            <MetadataKeySelect
                value={params.metadata_key}
                fieldNames={metadataFieldNames}
                onValueChange={(value) => onUpdate({ metadata_key: value })}
            />
        {/if}
    </div>
    <TargetDistributionModeSelect
        targetDistributionMode={params.target_distribution_mode}
        onUpdate={(mode) => onUpdate({ target_distribution_mode: mode })}
    />
    <StrengthField
        strength={params.strength}
        id={`metadata-class-balancing-strength-${instanceId}`}
        testid={`strategy-metadata-class-balancing-strength-input-${instanceId}`}
        min={0}
        onUpdate={(strength) => onUpdate({ strength })}
    />
    {#if params.target_distribution_mode === 'dictionary'}
        <TargetDistribution
            targetDistribution={params.target_distribution}
            annotationLabels={distinctValues}
            onUpdate={(rows) => onUpdate({ target_distribution: rows })}
        />
    {/if}
</div>
