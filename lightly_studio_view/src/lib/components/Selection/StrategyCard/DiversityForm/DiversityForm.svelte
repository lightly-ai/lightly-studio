<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
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
        <Label for="diversity-embedding-model">Embedding Model</Label>
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
        <Label for="diversity-strength">Strength</Label>
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
