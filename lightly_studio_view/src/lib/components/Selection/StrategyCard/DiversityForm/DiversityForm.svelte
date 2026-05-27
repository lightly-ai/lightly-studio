<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import FieldTooltip from '../../FieldTooltip.svelte';
    import type {
        DiversityParams,
        StrategyParams
    } from '../../useStrategyBuilder/useStrategyBuilder';

    interface Props {
        params: DiversityParams;
        onUpdate: (params: Partial<StrategyParams>) => void;
    }

    let { params, onUpdate }: Props = $props();
</script>

<div class="grid gap-3" data-testid="diversity-form">
    <div class="grid gap-2">
        <div class="flex items-center gap-1.5">
            <Label for="diversity-embedding-model">Embedding Model</Label>
            <FieldTooltip content="The model used to compute distances between samples. Leave blank to use the collection's default." />
        </div>
        <Input
            id="diversity-embedding-model"
            value={params.embedding_model_name}
            placeholder="Default embedding"
            oninput={(event) =>
                onUpdate({ embedding_model_name: (event.currentTarget as HTMLInputElement).value })}
            data-testid="strategy-diversity-embedding-model-input"
        />
    </div>
    <div class="grid gap-2">
        <div class="flex items-center gap-1.5">
            <Label for="diversity-strength">Strength</Label>
            <FieldTooltip content="Relative weight of this strategy in the combination. A strength of 2 gives this strategy twice the influence of one with strength 1. Must be a positive number." />
        </div>
        <Input
            id="diversity-strength"
            type="number"
            min="0"
            step="0.1"
            value={params.strength}
            oninput={(event) =>
                onUpdate({ strength: Number((event.currentTarget as HTMLInputElement).value) })}
            data-testid="strategy-diversity-strength-input"
        />
    </div>
</div>
