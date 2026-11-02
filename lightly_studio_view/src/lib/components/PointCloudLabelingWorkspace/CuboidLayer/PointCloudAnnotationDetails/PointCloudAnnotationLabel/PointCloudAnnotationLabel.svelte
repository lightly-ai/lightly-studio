<script lang="ts">
    import { useAnnotationLabels } from '$lib/hooks';
    import { SelectList } from '$lib/components/SelectList';
    import type { ListItem } from '$lib/components/SelectList/types';
    import LabelNotFound from '$lib/components/LabelNotFound/LabelNotFound.svelte';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';

    interface Props {
        collectionId: string;
        currentLabel: string;
        onSelect: (labelName: string) => void | Promise<void>;
    }

    let { collectionId, currentLabel, onSelect }: Props = $props();

    const labelsResult = useAnnotationLabels(() => ({ collectionId }));
    const items = $derived(getSelectionItems(labelsResult.data ?? []));

    function itemForLabel(label: string): ListItem {
        return items.find((i) => i.value === label) ?? { value: label, label };
    }

    let selectedItem: ListItem | undefined = $state();

    $effect(() => {
        selectedItem = itemForLabel(currentLabel);
    });

    async function handleSelect(item: ListItem) {
        try {
            await onSelect(item.value);
        } catch {
            selectedItem = itemForLabel(currentLabel);
        }
    }
</script>

<SelectList
    {items}
    bind:selectedItem
    name="annotation-label"
    placeholder="Select or create a class"
    className="w-full min-w-0"
    contentClassName="w-full min-w-0"
    onSelect={handleSelect}
>
    {#snippet notFound({ inputValue })}
        <LabelNotFound label={inputValue} />
    {/snippet}
</SelectList>
