<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import type {
        AnnotationLabelTable,
        CountAnnotationsView
    } from '$lib/api/lightly_studio_local/types.gen';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationCollectionsLabelFilter } from '$lib/hooks/useAnnotationCollectionsLabelFilter/useAnnotationCollectionsLabelFilter';
    import { onMount } from 'svelte';
    import AnnotationCollectionSection from './AnnotationCollectionSection.svelte';

    interface Props {
        collectionId: string;
        countsByCollectionLabelKey: Map<string, CountAnnotationsView>;
    }

    let { collectionId, countsByCollectionLabelKey }: Props = $props();

    const collectionsQuery = useAnnotationCollections({ collectionId });
    const { initializeAll, initialized, reset } = useAnnotationCollectionsLabelFilter();

    const collections = $derived(collectionsQuery.data ?? []);

    // Track loaded labels per annotation collection.
    let loadedLabelsMap = $state(new Map<string, AnnotationLabelTable[]>());

    onMount(() => {
        reset();
        loadedLabelsMap = new Map();
    });

    function areSameLabels(
        current: AnnotationLabelTable[] | undefined,
        next: AnnotationLabelTable[]
    ): boolean {
        if (!current || current.length !== next.length) return false;
        return current.every(
            (label, index) =>
                label.annotation_label_id === next[index]?.annotation_label_id &&
                label.annotation_label_name === next[index]?.annotation_label_name
        );
    }

    function handleLabelsLoaded(annotationCollectionId: string, labels: AnnotationLabelTable[]) {
        const currentLabels = loadedLabelsMap.get(annotationCollectionId);
        if (areSameLabels(currentLabels, labels)) {
            return;
        }
        loadedLabelsMap = new Map(loadedLabelsMap).set(annotationCollectionId, labels);
    }

    $effect(() => {
        if ($initialized || collections.length === 0) return;

        // Wait until every collection has reported its labels.
        const allLoaded = collections.every((c) => loadedLabelsMap.has(c.collection_id));
        if (!allLoaded) return;

        const withLabels = collections
            .map((c) => ({
                collectionId: c.collection_id,
                name: c.name,
                labels: (loadedLabelsMap.get(c.collection_id) ?? [])
                    .filter((l) => l.annotation_label_id != null)
                    .map((l) => ({
                        id: l.annotation_label_id!,
                        name: l.annotation_label_name
                    }))
            }))
            .filter((c) => c.labels.length > 0);

        initializeAll(withLabels);
    });
</script>

{#if collections.length > 0}
    <Segment title="Annotation Filters">
        <div class="space-y-2">
            {#each collections as collection (collection.collection_id)}
                <AnnotationCollectionSection
                    {collection}
                    {countsByCollectionLabelKey}
                    onLabelsLoaded={handleLabelsLoaded}
                />
            {/each}
        </div>
    </Segment>
{/if}
