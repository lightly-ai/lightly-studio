<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { MAX_INSTANCES_LIMIT } from '$lib/components/SampleDetails/FindInstancesOverlay/FindInstancesOverlay.helpers';

    interface Props {
        value: number;
        onChange: (value: number) => void;
    }

    let { value, onChange }: Props = $props();

    // Follows the parent value and holds the typed text until it is committed.
    let draft = $derived<number | null>(value);

    const commit = () => {
        // An empty or invalid field keeps the previous value.
        const typed = draft === null || Number.isNaN(draft) ? value : Math.round(draft);
        draft = Math.min(MAX_INSTANCES_LIMIT, Math.max(1, typed));
        onChange(draft);
    };
</script>

<label class="flex items-center justify-between gap-2 text-xs text-muted-foreground">
    Maximum instances
    <Input
        type="number"
        class="h-8 w-16"
        wrapperClass="w-auto"
        min={1}
        max={MAX_INSTANCES_LIMIT}
        bind:value={draft}
        onchange={commit}
    />
</label>
