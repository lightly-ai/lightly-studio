<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { SelectList } from '$lib/components/SelectList';
    import { AnnotationClassSelectList } from '$lib/components/AnnotationClassSelectList';

    type ListItem = ComponentProps<typeof SelectList>['items'][number];

    interface Props {
        label: string;
        placeholder: string;
        selectedName?: string;
        names: string[];
        disabled?: boolean;
        onSelect: (name: string) => void;
        // Picks only existing annotation classes instead of creating names.
        annotationClasses?: boolean;
    }

    let {
        label,
        placeholder,
        selectedName,
        names,
        disabled = false,
        onSelect,
        annotationClasses = false
    }: Props = $props();

    const Picker = $derived(annotationClasses ? AnnotationClassSelectList : SelectList);

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
    <Picker
        {items}
        {selectedItem}
        labelledBy={labelId}
        name={label}
        label={placeholder}
        placeholder={annotationClasses ? 'Search…' : 'Search or create…'}
        className="w-full"
        contentClassName="w-[var(--bits-popover-anchor-width)]"
        onSelect={handleSelect}
        {disabled}
    />
</div>
