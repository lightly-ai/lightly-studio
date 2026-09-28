<script lang="ts">
    import type { VideoAnnotationDetailsView } from '$lib/api/lightly_studio_local';
    import { Segment } from '$lib/components';
    import { routeHelpers } from '$lib/routes';
    import AnnotationViewSampleContainer from '../../AnnotationViewSampleContainer/AnnotationViewSampleContainer.svelte';

    interface Props {
        datasetId: string;
        video: VideoAnnotationDetailsView;
    }

    const { datasetId, video }: Props = $props();
</script>

<AnnotationViewSampleContainer
    href={routeHelpers.toVideosDetails({
        datasetId,
        collectionType: 'video',
        collectionId: video.sample.collection_id,
        sampleId: video.sample_id
    })}
>
    <Segment title="Video details">
        <div class="grid grid-cols-[6rem_1fr] gap-y-3 text-diffuse-foreground">
            <span class="text-sm">File name:</span>
            <span class="break-all text-sm">{video.file_name}</span>
            <span class="text-sm">File path:</span>
            <span class="break-all text-sm">{video.file_path_abs}</span>
        </div>
    </Segment>
</AnnotationViewSampleContainer>
