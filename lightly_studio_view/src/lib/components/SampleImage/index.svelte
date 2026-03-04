<script lang="ts">
    import { PUBLIC_SAMPLES_URL } from '$env/static/public';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { ImageSample } from '$lib/services/types';
    import { cn } from '$lib/utils';
    import { onMount } from 'svelte';
    import type { SampleImageObjectFit } from './types';

    const {
        sample,
        objectFit = 'contain',
        class: className,
        width,
        height
    }: {
        sample: Pick<ImageSample, 'sample_id' | 'file_path_abs' | 'sample'>;
        objectFit?: SampleImageObjectFit;
        class?: string;
        width?: number;
        height?: number;
    } = $props();

    const { getCollectionVersion } = useGlobalStorage();

    // Store the collection version to use for cache busting
    let collectionVersion = $state('');

    onMount(async () => {
        if (sample?.sample?.collection_id) {
            collectionVersion = await getCollectionVersion(sample.sample.collection_id);
        }
    });
</script>

<img
    src={`${PUBLIC_SAMPLES_URL}/sample/${sample.sample_id}${collectionVersion ? `?v=${collectionVersion}` : ''}`}
    alt={sample.file_path_abs}
    class={cn('sample-image rounded-lg bg-black', className)}
    style="--object-fit: {objectFit}"
    {width}
    {height}
    loading="lazy"
/>

<style>
    .sample-image {
        width: var(--sample-width);
        height: var(--sample-height);
        object-fit: var(--object-fit);
    }
</style>
