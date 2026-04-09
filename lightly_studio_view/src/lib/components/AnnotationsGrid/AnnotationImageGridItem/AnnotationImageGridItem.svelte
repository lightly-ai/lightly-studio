<script lang="ts">
    import type { AnnotationView, ImageAnnotationView } from '$lib/api/lightly_studio_local';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useSettings } from '$lib/hooks/useSettings';
    import { getGridImageURL, getGridThumbnailRequestSize } from '$lib/utils';
    import AnnotationItem from '../AnnotationItem/AnnotationItem.svelte';

    type Props = {
        annotation: AnnotationView;
        image: ImageAnnotationView;
        containerWidth: number;
        containerHeight: number;
        cachedCollectionVersion: string;
        showLabel: boolean;
        selected?: boolean;
    };

    let {
        annotation,
        containerWidth,
        containerHeight,
        image,
        cachedCollectionVersion = '',
        showLabel = true,
        selected = false
    }: Props = $props();

    const { getCollectionVersion } = useGlobalStorage();
    const { gridViewThumbnailQualityStore } = useSettings();

    // Store collection version for cache busting
    let collectionVersion = $state(cachedCollectionVersion);
    let collectionVersionLoaded = $state(!!cachedCollectionVersion);

    // Component is loaded when both collection version and image are loaded
    const isLoaded = $derived(collectionVersionLoaded);

    $effect(() => {
        if (!cachedCollectionVersion && image?.sample?.collection_id && !collectionVersionLoaded) {
            (async () => {
                const version = await getCollectionVersion(image.sample.collection_id);
                collectionVersion = version;
                collectionVersionLoaded = true;
            })();
        }

        if (cachedCollectionVersion && !collectionVersionLoaded) {
            collectionVersionLoaded = true;
        }
    });

    // Force CSS background to reload by using an incrementally different URL
    // This is a more aggressive approach to force the browser to reload the image
    const uniqueImageUrl = $derived(
        image
            ? getGridImageURL({
                  sampleId: image.sample_id,
                  quality: $gridViewThumbnailQualityStore,
                  renderedWidth: getGridThumbnailRequestSize(
                      containerWidth,
                      globalThis.window?.devicePixelRatio || 1
                  ),
                  renderedHeight: getGridThumbnailRequestSize(
                      containerHeight,
                      globalThis.window?.devicePixelRatio || 1
                  ),
                  cacheBuster: collectionVersion
              })
            : ''
    );

    const sample = $derived({
        width: image.width,
        height: image.height,
        url: uniqueImageUrl
    });
</script>

{#if isLoaded}
    <AnnotationItem
        {annotation}
        {containerHeight}
        {sample}
        {containerWidth}
        {showLabel}
        {selected}
    />
{/if}
