<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import type { MetadataWeightingParams, StrategyParams } from '$lib/hooks/useStrategyBuilder';
    import { StrengthField } from '$lib/components/Sampling/forms/StrengthField';
    import MetadataKeySelect from './MetadataKeySelect.svelte';
    interface Props {
        params: MetadataWeightingParams;
        metadataFieldNames?: string[];
        onUpdate: (params: Partial<StrategyParams>) => void;
    }
    let { params, metadataFieldNames = [], onUpdate }: Props = $props();
</script>

<div class="grid gap-3" data-testid="metadata-weighting-form">
    <div class="grid gap-2">
        <div class="flex items-center gap-1.5">
            <Label for="metadata-weighting-key">Metadata Key</Label>
            <FieldTooltip
                content="A numeric metadata field already indexed on this collection. Samples with higher values are weighted more heavily."
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
    <StrengthField
        strength={params.strength}
        id="metadata-weighting-strength"
        testid="strategy-metadata-weighting-strength-input"
        onUpdate={(strength) => onUpdate({ strength })}
    />
</div>
