<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import FieldTooltip from '../../FieldTooltip.svelte';
    import type {
        StrategyParams,
        TypicalityParams
    } from '../../useStrategyBuilder/useStrategyBuilder';

    interface Props {
        params: TypicalityParams;
        onUpdate: (params: Partial<StrategyParams>) => void;
    }

    let { params, onUpdate }: Props = $props();
</script>

<div class="grid gap-2" data-testid="typicality-form">
    <div class="flex items-center gap-1.5">
        <Label for="typicality-strength">Strength</Label>
        <FieldTooltip content="Relative weight of this strategy in the combination. A strength of 2 gives this strategy twice the influence of one with strength 1. Must be a positive number." />
    </div>
    <Input
        id="typicality-strength"
        type="number"
        min="0"
        step="0.1"
        value={params.strength}
        oninput={(event) =>
            onUpdate({ strength: Number((event.currentTarget as HTMLInputElement).value) })}
        data-testid="strategy-typicality-strength-input"
    />
</div>
