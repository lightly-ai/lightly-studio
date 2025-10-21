<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import AnnotationMetadata from './AnnotationMetadata/AnnotationMetadata.svelte';
    import SampleMetadata from '$lib/components/SampleMetadata/SampleMetadata.svelte';
    import { routeHelpers } from '$lib/routes';
    import Spinner from '$lib/components/Spinner/Spinner.svelte';
    import { page } from '$app/state';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';

    const {
        annotationId,
        onUpdate
    }: {
        annotationId: string;
        onUpdate?: () => void;
    } = $props();

    const { datasetId } = page.data;

    const { annotation: annotationResp } = $derived(
        useAnnotation({
            datasetId,
            annotationId
        })
    );

    let annotation = $derived($annotationResp.data);
    let sample = $derived(annotation?.sample);
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-hidden dark:[color-scheme:dark]"
        >
            <AnnotationMetadata {annotationId} {onUpdate} />

            {#if sample}
                <SampleMetadata {sample} showCustomMetadata={false} />

                <h2 class="py-2 text-lg font-semibold">
                    <a
                        href={routeHelpers.toSample({
                            sampleId: sample.sample_id,
                            datasetId: sample.dataset_id
                        })}
                        >Check all sample annotations
                    </a>
                </h2>
            {:else}
                <div class="flex h-full w-full items-center justify-center">
                    <Spinner size="large" align="center" />
                </div>
            {/if}
        </div>
    </CardContent>
</Card>
