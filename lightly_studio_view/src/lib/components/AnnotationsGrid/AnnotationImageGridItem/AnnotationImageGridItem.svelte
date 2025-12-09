<script lang="ts">
    import { PUBLIC_SAMPLES_URL } from '$env/static/public';
    import type {
        AnnotationView,
        ImageAnnotationView
    } from '$lib/api/lightly_studio_local';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import AnnotationItem from '../AnnotationItem/AnnotationItem.svelte';

    type Props = {
        annotation: AnnotationView;
        image: ImageAnnotationView;
        containerWidth: number;
        containerHeight: number;
        cachedDatasetVersion: string;
        showLabel: boolean;
        selected?: boolean;
    };

    let {
        annotation,
        containerWidth,
        containerHeight,
        image,
        cachedDatasetVersion = '',
        showLabel = true,
        selected = false
    }: Props = $props();

    const { getDatasetVersion } = useGlobalStorage();

    // Store dataset version for cache busting
    let datasetVersion = $state(cachedDatasetVersion);
    let datasetVersionLoaded = $state(!!cachedDatasetVersion);

    // Component is loaded when both dataset version and image are loaded
    const isLoaded = $derived(datasetVersionLoaded);

    $effect(() => {
        if (!cachedDatasetVersion && image?.sample?.dataset_id && !datasetVersionLoaded) {
            (async () => {
                const version = await getDatasetVersion(image.sample.dataset_id);
                datasetVersion = version;
                datasetVersionLoaded = true;
            })();
        }

        if (cachedDatasetVersion && !datasetVersionLoaded) {
            datasetVersionLoaded = true;
        }
    });

    // Force CSS background to reload by using an incrementally different URL
    // This is a more aggressive approach to force the browser to reload the image
    const uniqueImageUrl = $derived(
        image
            ? `${PUBLIC_SAMPLES_URL}/sample/${image.sample_id}${datasetVersion ? `?v=${datasetVersion}` : ''}`
            : ''
    );

    const sample = $derived({
        width: image.width,
        height: image.height,
        url: uniqueImageUrl
    });
</script>

<AnnotationItem {annotation} {containerHeight} {sample} {containerWidth} {showLabel} {selected} />
