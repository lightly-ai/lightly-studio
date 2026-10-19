<script lang="ts">
    import { useImageOrderBy } from '$lib/hooks/useImageOrderBy/useImageOrderBy';
    import { useGlobalStorage, usePostHog } from '$lib/hooks';
    import { type SelectItem } from '$lib/components/Select';
    import { getEvaluationMetricLabel } from '$lib/utils/evaluationMetricDisplay';
    import OrderByControl from './OrderByControl.svelte';

    interface Props {
        collectionId: string;
        datasetId: string;
    }

    const { collectionId, datasetId }: Props = $props();

    const { textEmbedding } = useGlobalStorage();
    const { trackEvent } = usePostHog();
    const isSimilaritySearchActive = $derived(!!$textEmbedding);

    const {
        allSortFields,
        selectedDirection,
        selectedLabel,
        isFieldSelected,
        handleFieldClick,
        toggleDirection,
        dispose
    } = useImageOrderBy({ collectionId: () => collectionId, datasetId: () => datasetId });

    $effect(() => {
        return () => dispose();
    });

    const selectValue = $derived.by(() => {
        const idx = $allSortFields.findIndex((field) => $isFieldSelected(field));
        return idx >= 0 ? String(idx) : '';
    });

    const sortItems = $derived<SelectItem[]>(
        $allSortFields.map((field, i) => ({
            value: String(i),
            label: field.source === 'evaluation_metric' ? field.evaluation_run_name : field.label,
            group:
                field.source === 'evaluation_metric'
                    ? (getEvaluationMetricLabel(field.metric_name) ?? field.metric_name)
                    : undefined,
            testId:
                field.source === 'evaluation_metric'
                    ? `sort-field-${field.evaluation_run_name}-${field.metric_name}`
                    : `sort-field-${field.value}`
        }))
    );

    const handleValueChange = (value: string) => {
        if (value === '') {
            const idx = $allSortFields.findIndex((field) => $isFieldSelected(field));
            if (idx >= 0) handleFieldClick($allSortFields[idx]);
            return;
        }
        const field = $allSortFields[Number(value)];
        if (field) handleFieldClick(field);
    };
    const isEvaluationSort = $derived(
        selectValue !== '' && $allSortFields[Number(selectValue)]?.source === 'evaluation_metric'
    );
</script>

<OrderByControl
    items={sortItems}
    selectedValue={selectValue}
    triggerLabel={$selectedLabel ?? undefined}
    direction={$selectedDirection}
    {isEvaluationSort}
    disabled={isSimilaritySearchActive}
    allowDeselect
    onValueChange={handleValueChange}
    onOpen={() => trackEvent('sort_by_opened', { collection_id: collectionId })}
    onToggleDirection={toggleDirection}
/>
