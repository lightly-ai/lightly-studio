<script lang="ts">
    import {
        SampleType,
        type AnnotationsFilter,
        type CollectionViewWithCount,
        type ImageFilter
    } from '$lib/api/lightly_studio_local';
    import Footer from '$lib/components/Footer/Footer.svelte';
    import { useAnnotationCounts } from '$lib/hooks/useAnnotationCounts/useAnnotationCounts';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useVideoFrameAnnotationCounts } from '$lib/hooks/useVideoFrameAnnotationsCount/useVideoFrameAnnotationsCount';
    import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds';
    import { useVideoAnnotationCounts } from '$lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount';
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
    import {
        buildVideoAnnotationCountsFilter,
        buildVideoFrameAnnotationCountsFilter
    } from '$lib/utils/buildAnnotationCountsFilters';
    import { buildImageFilter } from '$lib/utils/buildImageFilter';

    const {
        collection,
        collectionId,
        datasetId,
        isAnnotations,
        isVideoFrames,
        isVideos,
        parentCollectionId,
        parentSampleType
    }: {
        collection: CollectionViewWithCount;
        collectionId: string;
        datasetId: string;
        isAnnotations: boolean;
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
    const {
        selectedAnnotationFilterIds,
        filteredAnnotationCount,
        filteredSampleCount
    } = useGlobalStorage();

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

    const totalAnnotations = $derived.by(() => {
        const countsData = $annotationCounts.data;
        if (!countsData) {
            return 0;
        }

        return countsData.reduce((sum, item) => sum + Number(item.total_count), 0);
    });
</script>

<Footer
    totalSamples={collection?.total_sample_count}
    filteredSamples={$filteredSampleCount}
    {totalAnnotations}
    filteredAnnotations={$filteredAnnotationCount}
/>
