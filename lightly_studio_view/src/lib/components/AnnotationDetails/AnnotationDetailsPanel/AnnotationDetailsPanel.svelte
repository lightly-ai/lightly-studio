<script lang="ts">
    import { Card, CardContent, Spinner } from '$lib/components';
    import AnnotationMetadata from './AnnotationMetadata/AnnotationMetadata.svelte';
    import SampleMetadata from '$lib/components/SampleMetadata/SampleMetadata.svelte';
    import { routeHelpers } from '$lib/routes';
    import { useRemoveTagFromAnnotation } from '$lib/hooks/useRemoveTagFromAnnotation/useRemoveTagFromAnnotation';
    import SegmentTags from '../../SegmentTags/SegmentTags.svelte';
    import {
        SampleType,
        type AnnotationDetailsWithPayloadView,
        type ImageAnnotationDetailsView,
        type VideoFrameAnnotationDetailsView
    } from '$lib/api/lightly_studio_local';
    import AnnotationViewSampleContainer from '../AnnotationViewSampleContainer/AnnotationViewSampleContainer.svelte';
    import FrameDetailsSegment from '$lib/components/frames/FrameDetailsSegment/FrameDetailsSegment.svelte';

    const {
        annotationDetails,
        onUpdate
    }: {
        annotationDetails: AnnotationDetailsWithPayloadView;
        onUpdate: () => void;
    } = $props();
    const { removeTagFromAnnotation } = useRemoveTagFromAnnotation();

    const tags = $derived(
        annotationDetails?.annotation.tags?.map((t) => ({ tagId: t.tag_id, name: t.name })) ?? []
    );

    const onRemoveTag = async (tagId: string) => {
        await removeTagFromAnnotation(annotationDetails.annotation.sample_id, tagId);
    };
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-hidden dark:[color-scheme:dark]"
        >
            {#if annotationDetails?.annotation}
                <SegmentTags {tags} onClick={onRemoveTag} />
                <AnnotationMetadata annotation={annotationDetails.annotation} {onUpdate} />

                {#if annotationDetails.parent_sample_type == SampleType.IMAGE}
                    <AnnotationViewSampleContainer
                        href={routeHelpers.toSample({
                            sampleId: annotationDetails.parent_sample_data.sample_id,
                            datasetId: annotationDetails.parent_sample_data.sample.dataset_id
                        })}
                    >
                        <SampleMetadata
                            sample={annotationDetails.parent_sample_data as ImageAnnotationDetailsView}
                            showCustomMetadata={false}
                        />
                    </AnnotationViewSampleContainer>
                {:else if annotationDetails.parent_sample_type == SampleType.VIDEO}
                    <AnnotationViewSampleContainer
                        href={routeHelpers.toFramesDetails(
                            annotationDetails.parent_sample_data.sample.dataset_id,
                            annotationDetails.parent_sample_data.sample_id
                        )}
                    >
                        <FrameDetailsSegment
                            sample={annotationDetails.parent_sample_data as VideoFrameAnnotationDetailsView}
                        />
                    </AnnotationViewSampleContainer>
                {/if}
            {:else}
                <div class="flex h-full w-full items-center justify-center">
                    <Spinner size="large" align="center" />
                </div>
            {/if}
        </div>
    </CardContent>
</Card>
