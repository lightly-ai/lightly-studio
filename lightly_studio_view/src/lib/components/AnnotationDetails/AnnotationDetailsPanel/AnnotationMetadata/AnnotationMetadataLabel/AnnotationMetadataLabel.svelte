<script lang="ts">
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import type { Readable } from 'svelte/store';
    import LabelNotFound from '$lib/components/LabelNotFound/LabelNotFound.svelte';
    import { getSelectionItems } from '$lib/components/SelectList/getSelectionItems';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
    import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';

    const {
        label,
        value: currentValue = $bindable(),
        isEditingMode,
        datasetId,
        annotationId,
        onUpdate
    }: {
        label: string;
        value: string;
        isEditingMode: Readable<boolean>;
        datasetId: string;
        annotationId: string;
        onUpdate?: () => void;
    } = $props();

    const result = useAnnotationLabels({ datasetId });
    const { addReversibleAction } = useGlobalStorage();

    const { updateAnnotation, refetch } = useAnnotation({
        datasetId,
        annotationId,
        onUpdate
    });

    const { updateAnnotations: updateAnnotationsRaw } = useUpdateAnnotationsMutation({
        datasetId
    });

    const items = $derived(getSelectionItems($result.data || []));

    const value = $derived.by(() => {
        const item = items.find((i) => i.value === currentValue);
        return item ? item : { value: currentValue, label: currentValue };
    });
</script>

<span class="text-sm">{label}</span>

{#if $isEditingMode}
    <SelectList
        {items}
        selectedItem={items.find((i) => i.value === value?.value)}
        name="annotation-label"
        placeholder="Select or create a label"
        onSelect={(item) => {
            addAnnotationLabelChangeToUndoStack({
                annotations: [
                    {
                        sample_id: annotationId,
                        annotation_label: { annotation_label_name: currentValue }
                    }
                ],
                datasetId,
                addReversibleAction,
                updateAnnotations: updateAnnotationsRaw,
                refresh: refetch
            });

            updateAnnotation({
                annotation_id: annotationId,
                dataset_id: datasetId,
                label_name: item.value
            });
        }}
    >
        {#snippet notFound({ inputValue })}
            <LabelNotFound label={inputValue} />
        {/snippet}
    </SelectList>
{:else}
    <span class="break-all text-sm" data-testid={`annotation-metadata-label`}>{currentValue}</span>
{/if}
