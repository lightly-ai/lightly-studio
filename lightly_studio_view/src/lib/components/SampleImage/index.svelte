<script lang="ts">
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { ImageSample } from '$lib/services/types';
    import {
        cn,
        getGridImageURL,
        getGridThumbnailRequestSize,
        isMediaDirectUrlsEnabled,
        withProxyMediaMode
    } from '$lib/utils';
    import { onMount } from 'svelte';
    import type { SampleImageObjectFit } from './types';
    import type { GridThumbnailQuality } from '$lib/utils/getGridThumbnailURL/getGridThumbnailURL';

    const {
        sample,
        objectFit = 'contain',
        class: className,
        width,
        height,
        thumbnailQuality = 'raw',
        thumbnailWidth,
        thumbnailHeight
    }: {
        sample: Pick<ImageSample, 'sample_id' | 'file_path_abs' | 'sample'>;
        objectFit?: SampleImageObjectFit;
        class?: string;
        width?: number;
        height?: number;
        thumbnailQuality?: GridThumbnailQuality;
        thumbnailWidth?: number;
        thumbnailHeight?: number;
    } = $props();

    const { getCollectionVersion } = useGlobalStorage();

    // Store the collection version to use for cache busting
    let collectionVersion = $state('');

    onMount(async () => {
        if (sample?.sample?.collection_id) {
            collectionVersion = await getCollectionVersion(sample.sample.collection_id);
        }
    });

    const thumbnailUrl = $derived.by(() => {
        const devicePixelRatio = globalThis.window?.devicePixelRatio || 1;
        const renderedWidth =
            thumbnailWidth != null
                ? getGridThumbnailRequestSize(thumbnailWidth, devicePixelRatio)
                : undefined;
        const renderedHeight =
            thumbnailHeight != null
                ? getGridThumbnailRequestSize(thumbnailHeight, devicePixelRatio)
                : undefined;

        if (
            thumbnailQuality === 'high' &&
            ((renderedWidth ?? 0) > 0 || (renderedHeight ?? 0) > 0)
        ) {
            return getGridImageURL({
                sampleId: sample.sample_id,
                quality: thumbnailQuality,
                renderedWidth,
                renderedHeight,
                cacheBuster: collectionVersion
            });
        }

        return getGridImageURL({
            sampleId: sample.sample_id,
            quality: 'raw',
            cacheBuster: collectionVersion
        });
    });

    let displayedUrl = $state('');
    let fallbackAttempted = false;

    $effect(() => {
        displayedUrl = thumbnailUrl;
        fallbackAttempted = false;
    });

    async function handleImageError() {
        const failedUrl = displayedUrl;
        if (fallbackAttempted || !(await isMediaDirectUrlsEnabled())) return;
        if (displayedUrl !== failedUrl) return;
        fallbackAttempted = true;
        displayedUrl = withProxyMediaMode(failedUrl);
    }
</script>

<img
    src={displayedUrl}
    alt={sample.file_path_abs}
    class={cn('sample-image rounded-lg bg-black', className)}
    style="--object-fit: {objectFit}"
    {width}
    {height}
    draggable="false"
    loading="lazy"
    onerror={handleImageError}
/>

<style>
    .sample-image {
        width: var(--sample-width, 100%);
        height: var(--sample-height, 100%);
        object-fit: var(--object-fit);
    }
</style>
