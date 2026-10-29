<script lang="ts">
    import { useGlobalStorage, useImageFilters, useVideoFilters } from '$lib/hooks';
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
    const scope = $derived(
        describeExportScope({ count: $filteredSampleCount, sampleType, tagNames })
    );
</script>

<span class="block">{scope.summary}</span>
{#if scope.hint}
    <span class="mt-1 block text-sm text-muted-foreground">{scope.hint}</span>
{/if}
