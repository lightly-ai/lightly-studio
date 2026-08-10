<script lang="ts">
    import { useAnnotationOrderBy } from '$lib/hooks/useAnnotationOrderBy/useAnnotationOrderBy.svelte';
    import { useGlobalStorage, usePostHog } from '$lib/hooks';
    import { type SelectItem } from '$lib/components/Select';
    import OrderByControl from './OrderByControl.svelte';

    interface Props {
        /** The browsed annotation source. */
        collectionId: string;
    }

    const { collectionId }: Props = $props();

    const { textEmbedding } = useGlobalStorage();
    const { trackEvent } = usePostHog();
    // Similarity ordering keeps precedence over metric sorting, so the control is disabled
    // while a text or drag-to-search is active. The selection survives clearing the search.
    const isSimilaritySearchActive = $derived(!!$textEmbedding);

    const {
        allSortFields,
        selectedDirection,
        selectedIndex,
        handleFieldClick,
        toggleDirection,
        dispose
    } = useAnnotationOrderBy({ collectionId: () => collectionId });

    $effect(() => {
        return () => dispose();
    });

    const selectValue = $derived($selectedIndex >= 0 ? String($selectedIndex) : '');

    const sortItems = $derived<SelectItem[]>(
        $allSortFields.map((field, i) => ({
            value: String(i),
            label: field.label,
            testId: `sort-field-${field.evaluation_run_id}-${field.metric_name}`
        }))
    );

    const handleValueChange = (value: string) => {
        if (value === '') {
            if ($selectedIndex >= 0) handleFieldClick($allSortFields[$selectedIndex]);
            return;
        }
        const field = $allSortFields[Number(value)];
        if (field) handleFieldClick(field);
    };
</script>

<OrderByControl
    items={sortItems}
    selectedValue={selectValue}
    triggerLabel={$allSortFields[$selectedIndex]?.label}
    direction={$selectedDirection}
    disabled={isSimilaritySearchActive}
    allowDeselect
    onValueChange={handleValueChange}
    onOpen={() => trackEvent('sort_by_opened', { collection_id: collectionId })}
    onToggleDirection={toggleDirection}
/>
