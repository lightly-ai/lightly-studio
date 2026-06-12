<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';

    interface Props {
        strength: number;
        id: string;
        testid: string;
        min?: number;
        onUpdate: (strength: number) => void;
    }

    let { strength, id, testid, min, onUpdate }: Props = $props();

    const tooltipContent = $derived(
        min !== undefined && min >= 0
            ? 'Relative weight of this strategy in the combination. A strength of 2 gives this strategy twice the influence of one with strength 1.'
            : 'Relative weight of this strategy in the combination. A strength of 2 gives this strategy twice the influence of one with strength 1. Negative values invert the scoring direction.'
    );
</script>

<div class="grid gap-2">
    <div class="flex items-center gap-1.5">
        <Label for={id}>Strength</Label>
        <FieldTooltip content={tooltipContent} />
    </div>
    <Input
        {id}
        type="number"
        step="0.1"
        {min}
        value={strength}
        oninput={(event) => {
            const raw = (event.currentTarget as HTMLInputElement).value;
            const parsed = Number(raw);
            if (raw !== '' && !Number.isNaN(parsed) && (min === undefined || parsed >= min))
                onUpdate(parsed);
        }}
        data-testid={testid}
        class="[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
    />
</div>
