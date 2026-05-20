<script lang="ts">
    import { createQuery } from '@tanstack/svelte-query';
    import { readAnnotationLabelsForCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import type {
        AnnotationCollectionView,
        AnnotationLabelTable
    } from '$lib/api/lightly_studio_local/types.gen';
    import AnnotationColorLegend from '$lib/components/AnnotationColorLegend/AnnotationColorLegend.svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import { useAnnotationCollectionsLabelFilter } from '$lib/hooks/useAnnotationCollectionsLabelFilter/useAnnotationCollectionsLabelFilter';

    interface Props {
        collection: AnnotationCollectionView;
        onLabelsLoaded: (annotationCollectionId: string, labels: AnnotationLabelTable[]) => void;
    }

    let { collection, onLabelsLoaded }: Props = $props();

    const labelsQuery = createQuery(() =>
        readAnnotationLabelsForCollectionOptions({
            path: { annotation_collection_id: collection.collection_id }
        })
    );

    const {
        toggleCollection,
        toggleLabel,
        selectedLabels,
        allAvailableLabels,
        selectedCollectionIds,
        getCollectionCheckState
    } = useAnnotationCollectionsLabelFilter();

    const labels = $derived(labelsQuery.data ?? []);

    $effect(() => {
        // Report settled label queries, including empty collections, so parent initialization
        // does not wait forever when some annotation collections currently have no labels.
        if (labelsQuery.isSuccess) {
            onLabelsLoaded(collection.collection_id, labels);
        }
    });

    const checkState = $derived(
        getCollectionCheckState($selectedLabels, $allAvailableLabels, collection.collection_id)
    );
    const isIndeterminate = $derived(checkState === 'indeterminate');
    const isChecked = $derived(checkState === 'all');

    const useCollectionColor = $derived($selectedCollectionIds.length > 1);
</script>

{#if labels.length > 0}
    <div class="space-y-0.5">
        <!-- Collection header -->
        <div class="flex items-center space-x-2 py-1">
            <Checkbox
                id={`collection-${collection.collection_id}`}
                checked={isChecked}
                indeterminate={isIndeterminate}
                onCheckedChange={() => toggleCollection(collection.collection_id)}
            />
            <label
                for={`collection-${collection.collection_id}`}
                class="cursor-pointer truncate text-sm font-semibold"
                title={collection.name}
            >
                {collection.name}
            </label>
        </div>

        <!-- Label rows -->
        {#each labels as label (label.annotation_label_id)}
            {@const labelSelected =
                $selectedLabels
                    .get(collection.collection_id)
                    ?.has(label.annotation_label_id ?? '') ?? false}
            {@const colorName = useCollectionColor ? collection.name : label.annotation_label_name}
            <div
                class="flex items-center space-x-2 py-0.5 pl-6"
                title={label.annotation_label_name}
            >
                <Checkbox
                    id={`label-${collection.collection_id}-${label.annotation_label_id}`}
                    checked={labelSelected}
                    onCheckedChange={() => {
                        if (label.annotation_label_id) {
                            toggleLabel(collection.collection_id, label.annotation_label_id);
                        }
                    }}
                />
                <Label
                    for={`label-${collection.collection_id}-${label.annotation_label_id}`}
                    class="flex min-w-0 flex-1 cursor-pointer items-center space-x-2 text-nowrap peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                    <AnnotationColorLegend
                        labelName={colorName}
                        className="h-3 w-3"
                        selected={labelSelected}
                    />
                    <p class="flex-1 truncate text-base font-normal">
                        {label.annotation_label_name}
                    </p>
                </Label>
            </div>
        {/each}
    </div>
{/if}
