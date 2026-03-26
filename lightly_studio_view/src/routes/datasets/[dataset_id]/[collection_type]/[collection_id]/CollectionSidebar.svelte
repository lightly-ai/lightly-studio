<script lang="ts">
    import { SampleType, type AnnotationsFilter, type ImageFilter } from '$lib/api/lightly_studio_local';
    import type { AnnotationLabel } from '$lib/services/types';
    import CombinedMetadataDimensionsFilters from '$lib/components/CombinedMetadataDimensionsFilters/CombinedMetadataDimensionsFilters.svelte';
    import LabelsMenu from '$lib/components/LabelsMenu/LabelsMenu.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import TagCreateDialog from '$lib/components/TagCreateDialog/TagCreateDialog.svelte';
    import TagsMenu from '$lib/components/TagsMenu/TagsMenu.svelte';
    import { useAnnotationCounts } from '$lib/hooks/useAnnotationCounts/useAnnotationCounts';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useVideoFrameAnnotationCounts } from '$lib/hooks/useVideoFrameAnnotationsCount/useVideoFrameAnnotationsCount.js';
    import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds.js';
    import { useVideoAnnotationCounts } from '$lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.js';
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds.js';
    import {
        buildVideoAnnotationCountsFilter,
        buildVideoFrameAnnotationCountsFilter
    } from '$lib/utils/buildAnnotationCountsFilters';
    import { buildImageFilter } from '$lib/utils/buildImageFilter';
    import { SlidersHorizontal } from '@lucide/svelte';
    import { get, writable } from 'svelte/store';
    import type { GridType } from '$lib/types';

    type AnnotationCount = {
        label_name: string;
        total_count: number;
        current_count?: number;
    };

    const {
        collectionId,
        datasetId,
        gridType,
        isAnnotations,
        isSamples,
        isVideoFrames,
        isVideos,
        parentCollectionId,
        parentSampleType
    }: {
        collectionId: string;
        datasetId: string;
        gridType: GridType;
        isAnnotations: boolean;
        isSamples: boolean;
        isVideoFrames: boolean;
        isVideos: boolean;
        parentCollectionId?: string | null;
        parentSampleType?: SampleType | null;
    } = $props();

    const { metadataValues } = useMetadataFilters(collectionId);
    const { dimensionsValues } = useDimensions(collectionId);
    const { videoFramesBoundsValues } = useVideoFramesBounds(
        isVideoFrames || (isAnnotations && parentSampleType === SampleType.VIDEO_FRAME)
            ? isAnnotations && parentCollectionId
                ? parentCollectionId
                : collectionId
            : undefined
    );
    const { videoBoundsValues } = useVideoBounds(isVideos ? collectionId : undefined);
    const annotationLabels = $derived(useAnnotationLabels({ collectionId }));
    const {
        textEmbedding,
        selectedAnnotationFilterIds
    } = useGlobalStorage();

    const annotationFilterLabels = $derived.by(() =>
        $annotationLabels?.data
            ? $annotationLabels.data.reduce(
                  (acc: Record<string, string>, label: AnnotationLabel) => ({
                      ...acc,
                      [label.annotation_label_name!]: label.annotation_label_id!
                  }),
                  {} as Record<string, string>
              )
            : {}
    );

    const selectedAnnotationFilter = $derived.by(() => {
        const labelsMap = annotationFilterLabels;
        const currentSelectedIds = Array.from($selectedAnnotationFilterIds);

        return Object.entries(labelsMap)
            .filter(([, id]) => currentSelectedIds.includes(id))
            .map(([name]) => name);
    });

    const annotationFilter = $derived.by<AnnotationsFilter | undefined>(() =>
        $selectedAnnotationFilterIds.size > 0
            ? { annotation_label_ids: Array.from($selectedAnnotationFilterIds) }
            : undefined
    );
    const metadataFilters = $derived(
        $metadataValues ? createMetadataFilters($metadataValues) : undefined
    );
    const imageFilter = $derived.by<ImageFilter | undefined>(() =>
        buildImageFilter({
            dimensionsValues: $dimensionsValues ?? undefined,
            annotationFilter,
            metadataFilters,
            collectionId
        })
    );

    const annotationCounts = $derived.by(() => {
        if (
            isVideoFrames ||
            (isAnnotations && parentSampleType === SampleType.VIDEO_FRAME)
        ) {
            return useVideoFrameAnnotationCounts({
                collectionId: isAnnotations && parentCollectionId ? parentCollectionId : collectionId,
                filter: buildVideoFrameAnnotationCountsFilter({
                    metadataFilters,
                    annotationFilter,
                    videoFramesBoundsValues: $videoFramesBoundsValues
                })
            });
        }

        if (isVideos) {
            return useVideoAnnotationCounts({
                collectionId,
                filter: buildVideoAnnotationCountsFilter({
                    metadataFilters,
                    annotationFilter,
                    videoBoundsValues: $videoBoundsValues
                })
            });
        }

        return useAnnotationCounts({
            collectionId: datasetId,
            filter: imageFilter
        });
    });

    const annotationFilters = writable<
        Array<{
            label_name: string;
            total_count: number;
            current_count?: number;
            selected: boolean;
        }>
    >([]);

    const getAnnotationFilters = (annotations: Array<AnnotationCount>, selected: string[]) =>
        annotations.map((annotation) => ({
            ...annotation,
            selected: selected.includes(annotation.label_name)
        }));

    $effect(() => {
        const countsData = $annotationCounts.data;
        if (!countsData) {
            return;
        }

        annotationFilters.set(
            getAnnotationFilters(countsData as AnnotationCount[], selectedAnnotationFilter)
        );
    });

    const toggleAnnotationFilterSelection = (labelName: string) => {
        const labelId = annotationFilterLabels[labelName];
        if (!labelId) {
            return;
        }

        selectedAnnotationFilterIds.update((state: Set<string>) => {
            if (state.has(labelId)) {
                state.delete(labelId);
            } else {
                state.add(labelId);
            }

            return state;
        });
    };
</script>

<div class="flex h-full min-h-0 w-80 flex-col">
    <div class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card py-4">
        <div class="min-h-0 flex-1 space-y-2 overflow-y-auto px-4 pb-2 dark:[color-scheme:dark]">
            <div>
                <TagsMenu collection_id={collectionId} {gridType} />
                <TagCreateDialog
                    {collectionId}
                    {gridType}
                    {selectedAnnotationFilterIds}
                    textEmbedding={get(textEmbedding)}
                />
            </div>
            <Segment title="Filters" icon={SlidersHorizontal}>
                <div class="space-y-2">
                    <LabelsMenu
                        {annotationFilters}
                        onToggleAnnotationFilter={toggleAnnotationFilterSelection}
                    />

                    {#if isSamples || isVideos || isVideoFrames}
                        {#key collectionId}
                            <CombinedMetadataDimensionsFilters {isVideos} {isVideoFrames} />
                        {/key}
                    {/if}
                </div>
            </Segment>
        </div>
    </div>
</div>
