<script lang="ts">
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import type { ListItem } from '$lib/components/SelectList/types';

    type Props = {
        label: string;
        placeholder: string;
        selectedName?: string;
        names: string[];
        disabled?: boolean;
        onSelect: (name: string) => void;
    };

    let { label, placeholder, selectedName, names, disabled = false, onSelect }: Props = $props();

    const items = $derived(names.map((name) => ({ value: name, label: name })));
    const selectedItem = $derived(
        selectedName ? { value: selectedName, label: selectedName } : undefined
    );

    const handleSelect = (item: ListItem) => {
        onSelect(item.value);
    };
</script>

<div class="space-y-1.5">
    <div class="text-xs font-medium text-muted-foreground">{label}</div>
    <SelectList
        {items}
        {selectedItem}
        name={label}
        label={placeholder}
        placeholder="Search or create…"
        className="w-full"
        contentClassName="w-[var(--bits-popover-anchor-width)]"
        onSelect={handleSelect}
        onKeyboardConfirm={handleSelect}
        {disabled}
    />
</div>
