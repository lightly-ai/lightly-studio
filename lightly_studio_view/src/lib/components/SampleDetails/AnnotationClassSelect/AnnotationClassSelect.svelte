<script lang="ts">
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';
    import type { ListItem } from '$lib/components/SelectList/types';
    import { cn } from '$lib/utils';

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
    const items = $derived(getSelectionItems(annotationLabels.data ?? []));
    const selectedItem = $derived.by((): ListItem | undefined => {
        if (!value) return undefined;
        return items.find((item) => item.value === value) ?? { value, label: value };
    });
</script>

<SelectList
    {items}
    {selectedItem}
    name="annotation-class"
    {label}
    placeholder="Select or create an annotation class"
    className={cn('w-full', className)}
    contentClassName="w-full"
    isLoading={annotationLabels.isLoading}
    onSelect={(item) => onChange(item.value)}
/>
