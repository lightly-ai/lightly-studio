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

    const {
        annotationId,
        image,
        onUpdate
    }: {
        annotationId: string;
        image: ImageSample;
        onUpdate?: () => void;
    } = $props();
    const { removeTagFromAnnotation } = useRemoveTagFromAnnotation();

    const { datasetId } = page.data;

    const { annotation: annotationResp, refetch } = $derived(
        useAnnotation({
            datasetId,
            annotationId
        })
    );

    let annotation = $derived($annotationResp.data);

    const tags = $derived(annotation?.tags?.map((t) => ({ tagId: t.tag_id, name: t.name })) ?? []);

    const onRemoveTag = async (tagId: string) => {
        await removeTagFromAnnotation(annotation!.sample_id, tagId);
        refetch();
    };
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-hidden dark:[color-scheme:dark]"
        >
            <SegmentTags {tags} onClick={onRemoveTag} />
            <AnnotationMetadata {annotationId} {onUpdate} />

            {#if image}
                <SampleMetadata sample={image} showCustomMetadata={false} />

                <Button
                    variant="secondary"
                    href={routeHelpers.toSample({
                        sampleId: image.sample_id,
                        datasetId: image.sample.dataset_id
                    })}
                >
                    View sample
                </Button>
            {:else}
                <div class="flex h-full w-full items-center justify-center">
                    <Spinner size="large" align="center" />
                </div>
            {/if}
        </div>
    </CardContent>
</Card>
