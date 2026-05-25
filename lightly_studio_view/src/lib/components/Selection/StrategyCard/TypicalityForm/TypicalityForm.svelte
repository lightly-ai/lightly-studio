<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
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
    <Label for="typicality-strength">Strength</Label>
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
