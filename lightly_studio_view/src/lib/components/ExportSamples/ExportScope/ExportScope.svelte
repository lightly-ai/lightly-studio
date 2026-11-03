<script lang="ts">
    import {
        useAnnotationCollections,
        useAnnotationLabels,
        useGlobalStorage,
        useImageFilters,
        useVideoFilters
    } from '$lib/hooks';
    import { describeExportScope } from './describeExportScope';

    interface Props {
        /** The collection whose samples are exported. */
        collectionId: string;
        /** Sample type of the collection, e.g. 'image' or 'video'. */
        sampleType: string | undefined;
    }

    let { collectionId, sampleType }: Props = $props();

    const { filteredSampleCount, tags } = useGlobalStorage();
    const { imageFilter } = useImageFilters();
    const { videoFilter } = useVideoFilters();

    const tagNames = $derived.by(() => {
        const filter = sampleType === 'video' ? $videoFilter : $imageFilter;
        const tagIds = filter?.sample_filter?.tag_ids ?? [];
        const collectionTags = $tags[collectionId] ?? [];
        return tagIds.map((id) => collectionTags.find((tag) => tag.tag_id === id)?.name ?? id);
    });
    const sourcesQuery = useAnnotationCollections(() => ({ collectionId }));
    const labelsQuery = useAnnotationLabels(() => ({ collectionId }));
    const pairNames = $derived.by(() => {
        if (sampleType === 'video') return [];
        const pairs = $imageFilter?.sample_filter?.annotations_filter?.source_label_pairs ?? [];
        const sources = sourcesQuery.data ?? [];
        const labels = labelsQuery.data ?? [];
        return pairs.map((pair) => {
            const label = labels.find((l) => l.annotation_label_id === pair.annotation_label_id);
            const source = sources.find((c) => c.collection_id === pair.collection_id);
            return `${label?.annotation_label_name ?? pair.annotation_label_id} in ${source?.name ?? pair.collection_id}`;
        });
    });
    const scope = $derived(
        describeExportScope({ count: $filteredSampleCount, sampleType, tagNames, pairNames })
    );
</script>

<span class="block">{scope.summary}</span>
{#if scope.hint}
    <span class="mt-1 block text-sm text-muted-foreground">{scope.hint}</span>
{/if}
