<script lang="ts">
    import type { ImageView } from '$lib/api/lightly_studio_local';
    import { getSimilarityColor } from '$lib/utils';
    import { SampleAnnotations, SampleImage } from '..';
    import type { SampleImageObjectFit } from '../SampleImage/types';

    const {
        sample,
        objectFit,
        sampleSize,
        displayTextOnImage
    }: {
        sample: ImageView;
        objectFit?: SampleImageObjectFit;
        sampleSize: number;
        displayTextOnImage?: string;
    } = $props();
</script>

<SampleImage {sample} {objectFit} />
<SampleAnnotations
    {sample}
    containerWidth={sampleSize}
    sampleImageObjectFit={objectFit}
    containerHeight={sampleSize}
/>

{#if sample.similarity_score !== undefined && sample.similarity_score !== null}
    <div
        class="absolute right-1 z-10 flex items-center rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white backdrop-blur-sm {displayTextOnImage
            ? 'bottom-8'
            : 'bottom-1'}"
    >
        <span
            class="mr-1.5 block h-2 w-2 rounded-full"
            style="background-color: {getSimilarityColor(sample.similarity_score)}"
        ></span>
        {sample.similarity_score.toFixed(2)}
    </div>
{/if}
{#if displayTextOnImage}
    <div
        class="pointer-events-none absolute inset-x-0 bottom-0 z-10 rounded-b-lg bg-black/60 px-2 py-1 text-xs font-medium text-white"
    >
        <span class="block truncate" title={displayTextOnImage}>
            {displayTextOnImage}
        </span>
    </div>
{/if}
