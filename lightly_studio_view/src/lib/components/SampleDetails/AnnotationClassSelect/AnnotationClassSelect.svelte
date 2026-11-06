<script lang="ts">
    import { useAnnotationLabels } from '$lib/hooks';
    import { useCanCreateAnnotationClass } from '$lib/hooks';
    import { LabelNotFound } from '$lib/components/LabelNotFound';
    import { SelectList } from '$lib/components/SelectList';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';
    import type { ListItem } from '$lib/components/SelectList/types';
    import { cn, trackClassCreatedInPicker } from '$lib/utils';

    interface Props {
        collectionId: string;
        value?: string | null;
        onChange: (value: string) => void;
        label?: string;
        className?: string;
    }

    let {
        collectionId,
        value = null,
        onChange,
        label = 'Choose an annotation class',
        className = ''
    }: Props = $props();
    const annotationLabels = useAnnotationLabels(() => ({ collectionId }));
    const canCreateClass = useCanCreateAnnotationClass();
    const items = $derived(getSelectionItems(annotationLabels.data ?? []));
    const selectedItem = $derived.by((): ListItem | undefined => {
        if (value == null) return undefined;
        return items.find((item) => item.value === value) ?? { value, label: value };
    });
</script>

<SelectList
    onCreate={trackClassCreatedInPicker}
    allowCreate={canCreateClass}
    {items}
    {selectedItem}
    name="annotation-class"
    {label}
    placeholder="Select an annotation class"
    className={cn('w-full', className)}
    contentClassName="w-full"
    isLoading={annotationLabels.isLoading}
    onSelect={(item) => onChange(item.value)}
>
    {#snippet notFound({ inputValue })}
        <LabelNotFound label={inputValue} canCreate={canCreateClass} />
    {/snippet}
</SelectList>
