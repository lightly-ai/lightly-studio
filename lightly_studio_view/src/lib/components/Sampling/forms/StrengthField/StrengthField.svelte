<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';

    interface Props {
        strength: number;
        id: string;
        testid: string;
        onUpdate: (strength: number) => void;
    }

    let { strength, id, testid, onUpdate }: Props = $props();
</script>

<div class="grid gap-2">
    <div class="flex items-center gap-1.5">
        <Label for={id}>Strength</Label>
        <FieldTooltip
            content="Relative weight of this strategy in the combination. A strength of 2 gives this strategy twice the influence of one with strength 1. Must be a positive number."
        />
    </div>
    <Input
        {id}
        type="number"
        min="0"
        step="0.1"
        value={strength}
        oninput={(event) => onUpdate(Number((event.currentTarget as HTMLInputElement).value))}
        data-testid={testid}
    />
</div>
