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
        class: className
    }: {
        sample: Pick<ImageSample, 'sample_id' | 'file_path_abs' | 'sample'>;
        objectFit?: SampleImageObjectFit;
        class?: string;
    } = $props();

    const { getDatasetVersion } = useGlobalStorage();

    // Store the dataset version to use for cache busting
    let datasetVersion = $state('');

    onMount(async () => {
        if (sample?.sample?.dataset_id) {
            datasetVersion = await getDatasetVersion(sample.sample.dataset_id);
        }
    });
</script>

<img
    src={`${PUBLIC_SAMPLES_URL}/sample/${sample.sample_id}${datasetVersion ? `?v=${datasetVersion}` : ''}`}
    alt={sample.file_path_abs}
    class={cn('sample-image rounded-lg bg-black', className)}
    style="--object-fit: {objectFit}"
    loading="lazy"
/>

<style>
    .sample-image {
        width: var(--sample-width);
        height: var(--sample-height);
        object-fit: var(--object-fit);
    }
</style>
