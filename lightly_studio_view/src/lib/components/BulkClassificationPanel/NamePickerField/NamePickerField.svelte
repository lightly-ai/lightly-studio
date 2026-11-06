<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { SelectList } from '$lib/components/SelectList';
    import { LabelNotFound } from '$lib/components/LabelNotFound';

    type ListItem = ComponentProps<typeof SelectList>['items'][number];

    interface Props {
        label: string;
        placeholder: string;
        selectedName?: string;
        names: string[];
        disabled?: boolean;
        allowCreate?: boolean;
        onSelect: (name: string) => void;
        onCreate?: () => void;
    }

    let {
        label,
        placeholder,
        selectedName,
        names,
        disabled = false,
        allowCreate = true,
        onSelect,
        onCreate
    }: Props = $props();

    const labelId = $props.id();

    const items = $derived(names.map((name) => ({ value: name, label: name })));
    const selectedItem = $derived(
        selectedName ? { value: selectedName, label: selectedName } : undefined
    );

    const handleSelect = (item: ListItem) => {
        onSelect(item.value);
    };
</script>

{#snippet classNotFound({ inputValue }: { inputValue: string })}
    <LabelNotFound label={inputValue} canCreate={false} />
{/snippet}

<div class="space-y-1.5">
    <div id={labelId} class="text-xs font-medium text-muted-foreground">{label}</div>
    <SelectList
        {items}
        {selectedItem}
        labelledBy={labelId}
        name={label}
        label={placeholder}
        placeholder={allowCreate ? 'Search or create…' : 'Search…'}
        {allowCreate}
        className="w-full"
        contentClassName="w-[var(--bits-popover-anchor-width)]"
        onSelect={handleSelect}
        {onCreate}
        {disabled}
        notFound={allowCreate ? undefined : classNotFound}
    />
</div>
