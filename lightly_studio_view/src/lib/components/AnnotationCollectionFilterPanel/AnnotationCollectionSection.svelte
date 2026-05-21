<script lang="ts">
    import { createQuery } from '@tanstack/svelte-query';
    import { readAnnotationLabelsForCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import type {
        AnnotationCollectionView,
        AnnotationLabelTable,
        CountAnnotationsView
    } from '$lib/api/lightly_studio_local/types.gen';
    import AnnotationColorLegend from '$lib/components/AnnotationColorLegend/AnnotationColorLegend.svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import { useAnnotationCollectionsLabelFilter } from '$lib/hooks/useAnnotationCollectionsLabelFilter/useAnnotationCollectionsLabelFilter';
    import { formatInteger } from '$lib/utils';
    import {
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger
    } from '$lib/components/ui/collapsible';
    import { ChevronDown } from '@lucide/svelte';
    import { slide } from 'svelte/transition';

    interface Props {
        collection: AnnotationCollectionView;
        countsByCollectionLabelKey: Map<string, CountAnnotationsView>;
        onLabelsLoaded: (annotationCollectionId: string, labels: AnnotationLabelTable[]) => void;
    }

    let { collection, countsByCollectionLabelKey, onLabelsLoaded }: Props = $props();

    const getCountKey = (annotationCollectionId: string, labelName: string) =>
        `${annotationCollectionId}:${labelName}`;

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
    const collectionCounts = $derived.by(() =>
        labels.reduce(
            (summary, label) => {
                const count = countsByCollectionLabelKey.get(
                    getCountKey(collection.collection_id, label.annotation_label_name)
                );
                if (!count) {
                    return summary;
                }
                return {
                    current: summary.current + count.current_count,
                    total: summary.total + count.total_count
                };
            },
            { current: 0, total: 0 }
        )
    );

    let sectionOpen = $state(false);
    const duration = 168;
</script>

{#if labels.length > 0}
    <Collapsible bind:open={sectionOpen}>
        <div class="space-y-0.5">
            <!-- Collection header -->
            <div class="flex items-center space-x-2 py-1">
                <Checkbox
                    id={`collection-${collection.collection_id}`}
                    checked={isChecked}
                    indeterminate={isIndeterminate}
                    onCheckedChange={() => toggleCollection(collection.collection_id)}
                />
                <CollapsibleTrigger class="flex flex-1 items-center justify-between gap-1 overflow-hidden">
                    <span
                        class="truncate text-sm font-semibold"
                        title={collection.name}
                    >
                        {collection.name}
                    </span>
                    <div class="flex items-center gap-2">
                        {#if collectionCounts.total > 0}
                            <span class="text-sm font-normal text-diffuse-foreground">
                                {formatInteger(collectionCounts.current)} of
                                {formatInteger(collectionCounts.total)}
                            </span>
                        {/if}
                        <ChevronDown
                            class="h-4 w-4 shrink-0 transition-transform duration-{duration}"
                            style={`transform: ${sectionOpen ? 'rotate(-180deg)' : 'rotate(0deg)'}`}
                        />
                    </div>
                </CollapsibleTrigger>
            </div>

            <!-- Label rows -->
            <CollapsibleContent forceMount>
                {#if sectionOpen}
                    <div class="space-y-0.5" transition:slide={{ duration }}>
                        {#each labels as label (label.annotation_label_id)}
                            {@const labelSelected =
                                $selectedLabels
                                    .get(collection.collection_id)
                                    ?.has(label.annotation_label_id ?? '') ?? false}
                            {@const labelCounts = countsByCollectionLabelKey.get(
                                getCountKey(collection.collection_id, label.annotation_label_name)
                            )}
                            {@const colorName = useCollectionColor
                                ? collection.name
                                : label.annotation_label_name}
                            <div
                                class="flex items-center space-x-2 py-0.5 pl-6"
                                title={label.annotation_label_name}
                            >
                                <Checkbox
                                    id={`label-${collection.collection_id}-${label.annotation_label_id}`}
                                    checked={labelSelected}
                                    onCheckedChange={() => {
                                        if (label.annotation_label_id) {
                                            toggleLabel(
                                                collection.collection_id,
                                                label.annotation_label_id
                                            );
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
                                    {#if labelCounts}
                                        <span class="text-sm text-diffuse-foreground">
                                            {formatInteger(labelCounts.current_count)} of
                                            {formatInteger(labelCounts.total_count)}
                                        </span>
                                    {/if}
                                </Label>
                            </div>
                        {/each}
                    </div>
                {/if}
            </CollapsibleContent>
        </div>
    </Collapsible>
{/if}
