<script lang="ts">
    import { Checkbox } from '$lib/components';
    import type { GridType } from '$lib/types';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Tags as Tagsicon } from '@lucide/svelte';
    import type { TagView } from '$lib/services/types';
    import { useTags } from '$lib/hooks/useTags/useTags.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import {
        createTag,
        addSampleIdsToTagId,
        readImages,
        type ReadImagesRequest,
        getAllFrames,
        type VideoFrameFilter,
        type VideoFilter,
        getVideoSampleIds,
        readAnnotationsWithPayload,
        type SampleFilter
    } from '$lib/api/lightly_studio_local';
    import TagAssignInput from './TagAssignInput.svelte';
    import { toast } from 'svelte-sonner';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds';
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
    import { isNormalModeParams } from '$lib/hooks/useImagesInfinite/useImagesInfinite';

    let { collection_id, gridType }: Parameters<typeof useTags>[0] & { gridType: GridType } =
        $props();

    const tagKind = $derived(gridType === 'annotations' ? 'annotation' : 'sample');

    const { tags, tagsSelected, tagSelectionToggle, loadTags } = $derived(
        useTags({ collection_id, kind: [tagKind] })
    );

    const { getSelectedSampleIds, selectedSampleAnnotationCropIds } = useGlobalStorage();
    const { metadataValues } = useMetadataFilters(collection_id);
    const { dimensionsValues: dimensions } = useDimensions();
    const { filterParams } = useImageFilters();
    const { filterParams: videoFilterParams } = useVideoFilters();
    const { videoFramesBoundsValues } = useVideoFramesBounds();
    const { videoBoundsValues } = useVideoBounds();
    const { annotationLabelIds, annotationFilter } = useSelectedAnnotationsFilter(collection_id);

    const selectedSampleIds = $derived(getSelectedSampleIds(collection_id));
    const selectedIds = $derived(
        tagKind === 'annotation'
            ? ($selectedSampleAnnotationCropIds[collection_id] ?? new Set<string>())
            : $selectedSampleIds
    );
    const sampleFilter = $derived<SampleFilter>({
        annotations_filter: $annotationFilter,
        tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
        metadata_filters: $metadataValues ? createMetadataFilters($metadataValues) : undefined
    });
    const imageParams = $derived<ReadImagesRequest>({
        filters: {
            sample_filter: {
                sample_ids: isNormalModeParams($filterParams)
                    ? $filterParams.filters?.sample_ids
                    : undefined,
                ...sampleFilter
            },
            ...($dimensions ?? {})
        }
    });
    const videoFramesFilter = $derived<VideoFrameFilter>({
        sample_filter: {
            ...sampleFilter
        },
        ...$videoFramesBoundsValues
    });
    const videosFilter = $derived<VideoFilter>({
        frame_annotation_filter: $annotationFilter,
        sample_filter: {
            sample_ids: $videoFilterParams?.filters?.sample_ids,
            ...sampleFilter,
            annotations_filter: undefined
        },
        ...$videoBoundsValues
    });
    const annotationsQueryParams = $derived({
        annotation_label_ids: $annotationLabelIds,
        tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined
    });

    // ── Selection assignment ─────────────────────────────────────────────────────
    let assignBusy = $state(false);

    async function getCurrentViewIds(): Promise<string[]> {
        if (gridType === 'samples') {
            const response = await readImages({
                path: { collection_id },
                body: imageParams
            });
            return response.data?.data?.map((sample) => sample.sample_id) ?? [];
        }

        if (gridType === 'video_frames') {
            const response = await getAllFrames({
                path: { video_frame_collection_id: collection_id },
                body: { filter: videoFramesFilter }
            });
            return response.data?.data?.map((frame) => frame.sample_id) ?? [];
        }

        if (gridType === 'videos') {
            const response = await getVideoSampleIds({
                path: { collection_id },
                body: { filter: videosFilter }
            });
            return response.data ?? [];
        }

        if (gridType === 'annotations') {
            const response = await readAnnotationsWithPayload({
                path: { collection_id },
                query: annotationsQueryParams
            });
            return response.data?.data?.map((annotation) => annotation.annotation.sample_id) ?? [];
        }

        return [];
    }

    async function handleAssign(name: string) {
        assignBusy = true;
        const sampleIds =
            selectedIds.size > 0 ? [...selectedIds] : Array.from(new Set(await getCurrentViewIds()));

        if (sampleIds.length === 0) {
            assignBusy = false;
            toast.error('No items found in the current view.');
            return;
        }

        const existingTag = $tags.find((t: TagView) => t.name.toLowerCase() === name.toLowerCase());
        if (existingTag) {
            const response = await addSampleIdsToTagId({
                path: { collection_id, tag_id: existingTag.tag_id },
                body: { sample_ids: sampleIds }
            });
            assignBusy = false;
            if (response.error) {
                toast.error('Failed to assign tag. Please try again.');
                return;
            }
        } else {
            const createResponse = await createTag({
                path: { collection_id },
                body: { name, description: `${name} description`, kind: tagKind }
            });
            if (createResponse.error || !createResponse.data?.tag_id) {
                assignBusy = false;
                toast.error('Failed to create tag. Please try again.');
                return;
            }
            const assignResponse = await addSampleIdsToTagId({
                path: { collection_id, tag_id: createResponse.data.tag_id },
                body: { sample_ids: sampleIds }
            });
            assignBusy = false;
            if (assignResponse.error) {
                toast.error('Failed to assign tag. Please try again.');
                return;
            }
        }
        loadTags();
    }
</script>

<Segment title="Tags" icon={Tagsicon}>
    <div class="mb-3 w-full space-y-1">
        <div class="space-y-1">
            {#each $tags as tag (tag.tag_id)}
                <div class="flex items-center py-0.5" data-testid="tag-menu-item">
                    <Checkbox
                        name={tag.tag_id}
                        isChecked={$tagsSelected.has(tag.tag_id)}
                        label={tag.name}
                        onCheckedChange={() => tagSelectionToggle(tag.tag_id)}
                    />
                </div>
            {:else}
                <p>No tags yet</p>
            {/each}
        </div>

        <TagAssignInput
            options={$tags}
            busy={assignBusy}
            onSelect={handleAssign}
        />
    </div>
</Segment>
