<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import type { DeduplicationParams, StrategyParams } from '$lib/hooks/useStrategyBuilder';
    import { StrengthField } from '$lib/components/Sampling/forms/StrengthField';

    interface Props {
        params: DeduplicationParams;
        onUpdate: (params: Partial<StrategyParams>) => void;
    }
    let { params, onUpdate }: Props = $props();
</script>

<div class="grid gap-3" data-testid="deduplication-form">
    <div class="grid gap-2">
        <div class="flex items-center gap-1.5">
            <Label for="deduplication-min-distance">Minimum Distance</Label>
            <FieldTooltip
                content="Selection stops once no remaining sample is at least this far from the already selected samples in embedding space. Larger values keep fewer, more distinct samples."
            />
        </div>
        <Input
            id="deduplication-min-distance"
            type="number"
            step="0.001"
            min={0}
            value={params.stopping_condition_minimum_distance}
            oninput={(event) => {
                const raw = (event.currentTarget as HTMLInputElement).value;
                const parsed = Number(raw);
                if (raw !== '' && !Number.isNaN(parsed) && parsed > 0) {
                    onUpdate({ stopping_condition_minimum_distance: parsed });
                }
            }}
            data-testid="strategy-deduplication-min-distance-input"
            class="[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        />
    </div>
    <StrengthField
        strength={params.strength}
        id="deduplication-strength"
        testid="strategy-deduplication-strength-input"
        min={0}
        onUpdate={(strength) => onUpdate({ strength })}
    />
</div>
