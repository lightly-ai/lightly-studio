<script lang="ts">
    import { useAnnotationLabels } from '$lib/hooks';
    import { SelectList } from '$lib/components/SelectList';
    import LabelNotFound from '$lib/components/LabelNotFound/LabelNotFound.svelte';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';

    interface Props {
        collectionId: string;
        currentLabel: string;
        onSelect: (labelName: string) => void;
    }

    let { collectionId, currentLabel, onSelect }: Props = $props();

    const labelsResult = useAnnotationLabels(() => ({ collectionId }));
    const items = $derived(getSelectionItems(labelsResult.data ?? []));
    const selectedItem = $derived(
        items.find((i) => i.value === currentLabel) ?? { value: currentLabel, label: currentLabel }
    );
</script>

<SelectList
    {items}
    {selectedItem}
    name="annotation-label"
    placeholder="Select or create a class"
    className="w-full min-w-0"
    contentClassName="w-full min-w-0"
    onSelect={(item) => onSelect(item.value)}
>
    {#snippet notFound({ inputValue })}
        <LabelNotFound label={inputValue} />
    {/snippet}
</SelectList>
