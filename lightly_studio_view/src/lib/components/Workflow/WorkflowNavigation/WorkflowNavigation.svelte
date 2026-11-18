<script lang="ts">
    import { goto, preloadData } from '$app/navigation';
    import { page } from '$app/state';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { routeHelpers } from '$lib/routes';
    import { toBatchSampleURL } from '$lib/components/Workflow/datasetNavigation';

    interface Props {
        previousSampleId: string | null;
        nextSampleId: string | null;
    }

    const { previousSampleId, nextSampleId }: Props = $props();

    const { context } = useAnnotationLabelContext();

    const toURL = (sampleId: string | null) =>
        sampleId
            ? toBatchSampleURL(
                  routeHelpers.toSample({
                      sampleId,
                      datasetId: page.params.dataset_id!,
                      collectionType: page.params.collection_type!,
                      collectionId: page.params.collection_id!
                  }),
                  page.url
              )
            : null;

    const previousURL = $derived(toURL(previousSampleId));
    const nextURL = $derived(toURL(nextSampleId));

    $effect(() => {
        if (nextURL) preloadData(nextURL);
        if (previousURL) preloadData(previousURL);
    });
</script>

<SteppingNavigation
    hasPrevious={previousURL !== null}
    hasNext={nextURL !== null}
    onPrevious={() => previousURL && goto(previousURL)}
    onNext={() => nextURL && goto(nextURL)}
    isDrawing={context?.isDrawing}
/>
