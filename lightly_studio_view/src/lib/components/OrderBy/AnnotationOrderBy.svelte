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

    const DEFAULT_VALUE = 'default';

    const { textEmbedding } = useGlobalStorage();
    const { trackEvent } = usePostHog();
    // Similarity ordering keeps precedence over metric sorting, so the control is disabled
    // while a text or drag-to-search is active. The selection survives clearing the search.
    const isSimilaritySearchActive = $derived(!!$textEmbedding);

    const {
        allSortFields,
        selectedDirection,
        selectedLabel,
        isFieldSelected,
        handleFieldClick,
        clearSort,
        toggleDirection,
        dispose
    } = useAnnotationOrderBy({ collectionId: () => collectionId });

    $effect(() => {
        return () => dispose();
    });

    const selectValue = $derived.by(() => {
        const idx = $allSortFields.findIndex((field) => $isFieldSelected(field));
        return idx >= 0 ? String(idx) : DEFAULT_VALUE;
    });

    const sortItems = $derived<SelectItem[]>([
        { value: DEFAULT_VALUE, label: 'Default', testId: 'sort-field-default' },
        ...$allSortFields.map((field, i) => ({
            value: String(i),
            label: field.label,
            testId: `sort-field-${field.evaluation_run_id}-${field.metric_name}`
        }))
    ]);

    const handleValueChange = (value: string) => {
        if (value === DEFAULT_VALUE) {
            clearSort();
            return;
        }
        const field = $allSortFields[Number(value)];
        if (field) handleFieldClick(field);
    };
</script>

<OrderByControl
    items={sortItems}
    selectedValue={selectValue}
    triggerLabel={$selectedLabel ?? undefined}
    direction={$selectedDirection}
    disabled={isSimilaritySearchActive}
    onValueChange={handleValueChange}
    onOpen={() => trackEvent('sort_by_opened', { collection_id: collectionId })}
    onToggleDirection={toggleDirection}
/>
