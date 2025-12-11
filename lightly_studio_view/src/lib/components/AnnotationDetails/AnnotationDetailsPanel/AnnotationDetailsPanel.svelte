<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import AnnotationMetadata from './AnnotationMetadata/AnnotationMetadata.svelte';
    import SampleMetadata from '$lib/components/SampleMetadata/SampleMetadata.svelte';
    import { routeHelpers } from '$lib/routes';
    import Spinner from '$lib/components/Spinner/Spinner.svelte';
    import { page } from '$app/state';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import Button from '$lib/components/ui/button/button.svelte';
    import { useRemoveTagFromAnnotation } from '$lib/hooks/useRemoveTagFromAnnotation/useRemoveTagFromAnnotation';
    import SegmentTags from '../../SegmentTags/SegmentTags.svelte';
    import type { ImageSample } from '$lib/services/types';
    import { SampleType, type AnnotationDetailsWithPayloadView } from '$lib/api/lightly_studio_local';
    import AnnotationViewSampleContainer from '../AnnotationViewSampleContainer/AnnotationViewSampleContainer.svelte';

    const {
        annotationId,
        annotationDetails,
        onUpdate
    }: {
        annotationId: string;
        annotationDetails: AnnotationDetailsWithPayloadView
        onUpdate: () => void;
    } = $props();
    const { removeTagFromAnnotation } = useRemoveTagFromAnnotation();

    const tags = $derived(annotationDetails.annotation.tags?.map((t) => ({ tagId: t.tag_id, name: t.name })) ?? []);

    const onRemoveTag = async (tagId: string) => {
        await removeTagFromAnnotation(annotationDetails.annotation.sample_id, tagId);
        
    };
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-hidden dark:[color-scheme:dark]"
        >
            <SegmentTags {tags} onClick={onRemoveTag} />
            <AnnotationMetadata {annotationId} {onUpdate} />

            {#if annotationDetails.parent_sample_type == SampleType.IMAGE}
                <AnnotationViewSampleContainer href={routeHelpers.toSample({
                        sampleId: annotationDetails.parent_sample_data.sample_id,
                        datasetId: annotationDetails.parent_sample_data.sample.dataset_id
                    })}>
                    <SampleMetadata sample={annotationDetails.parent_sample_data} showCustomMetadata={false} />
                </AnnotationViewSampleContainer>
            {:else}
                <div class="flex h-full w-full items-center justify-center">
                    <Spinner size="large" align="center" />
                </div>
            {/if}
        </div>
    </CardContent>
</Card>
