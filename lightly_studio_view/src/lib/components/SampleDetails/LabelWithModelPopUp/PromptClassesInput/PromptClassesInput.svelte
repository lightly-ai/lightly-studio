<script lang="ts">
    import { untrack } from 'svelte';
    import { Input } from '$lib/components/ui/input';

    interface Props {
        classNames: string[];
        onChange: (classNames: string[]) => void;
    }

    let { classNames, onChange }: Props = $props();

    // Kept as typed, so a trailing comma does not jump away while the user types. The parent
    // remounts the input for another model.
    let text = $state(untrack(() => classNames.join(', ')));

    const toClassNames = (value: string) => [
        ...new Set(
            value
                .split(',')
                .map((name) => name.trim())
                .filter((name) => name.length > 0)
        )
    ];
</script>

<label class="grid gap-1.5 text-xs text-muted-foreground">
    What to find
    <Input
        class="h-8 text-sm"
        placeholder="forklift, pallet, person"
        value={text}
        oninput={(event) => {
            text = event.currentTarget.value;
            onChange(toClassNames(text));
        }}
    />
</label>
