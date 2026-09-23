<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { SelectList } from '$lib/components/SelectList';

    type ListItem = ComponentProps<typeof SelectList>['items'][number];

    interface Props {
        label: string;
        placeholder: string;
        selectedName?: string;
        names: string[];
        disabled?: boolean;
        onSelect: (name: string) => void;
    }

    let { label, placeholder, selectedName, names, disabled = false, onSelect }: Props = $props();

    const labelId = $props.id();

    const items = $derived(names.map((name) => ({ value: name, label: name })));
    const selectedItem = $derived(
        selectedName ? { value: selectedName, label: selectedName } : undefined
    );

    const handleSelect = (item: ListItem) => {
        onSelect(item.value);
    };
</script>

<div class="space-y-1.5">
    <div id={labelId} class="text-xs font-medium text-muted-foreground">{label}</div>
    <SelectList
        {items}
        {selectedItem}
        labelledBy={labelId}
        name={label}
        label={placeholder}
        placeholder="Search or create…"
        className="w-full"
        contentClassName="w-[var(--bits-popover-anchor-width)]"
        onSelect={handleSelect}
        {disabled}
    />
</div>
