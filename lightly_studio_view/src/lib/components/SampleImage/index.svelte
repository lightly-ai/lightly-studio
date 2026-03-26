<script lang="ts">
    import { PUBLIC_SAMPLES_URL } from '$env/static/public';
    import type { ImageSample } from '$lib/services/types';
    import { cn } from '$lib/utils';
    import type { SampleImageObjectFit } from './types';

    const {
        sample,
        objectFit = 'contain',
        class: className,
        cachedCollectionVersion = '',
        width,
        height
    }: {
        sample: Pick<ImageSample, 'sample_id' | 'file_path_abs' | 'sample'>;
        objectFit?: SampleImageObjectFit;
        class?: string;
        cachedCollectionVersion?: string;
        width?: number;
        height?: number;
    } = $props();
</script>

<img
    src={`${PUBLIC_SAMPLES_URL}/sample/${sample.sample_id}${cachedCollectionVersion ? `?v=${cachedCollectionVersion}` : ''}`}
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
