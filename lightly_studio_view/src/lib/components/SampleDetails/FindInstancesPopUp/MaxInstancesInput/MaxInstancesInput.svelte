<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { MAX_INSTANCES_LIMIT } from '$lib/components/SampleDetails/FindInstancesOverlay/FindInstancesOverlay.helpers';

    interface Props {
        value: number;
        onChange: (value: number) => void;
    }

    let { value, onChange }: Props = $props();

    const clamp = (input: number) =>
        Math.min(MAX_INSTANCES_LIMIT, Math.max(1, Math.round(input) || 1));
</script>

<label class="flex items-center justify-between gap-2 text-xs text-muted-foreground">
    Maximum instances
    <Input
        type="number"
        class="h-8 w-16"
        wrapperClass="w-auto"
        min={1}
        max={MAX_INSTANCES_LIMIT}
        {value}
        onchange={(event) => {
            const clamped = clamp(event.currentTarget.valueAsNumber);
            event.currentTarget.value = String(clamped);
            onChange(clamped);
        }}
    />
</label>
