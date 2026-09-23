<script lang="ts">
    import type { ImageView } from '$lib/api/lightly_studio_local';
    import SampleClassificationPills from '$lib/components/SampleClassificationPills/SampleClassificationPills.svelte';
    import SampleValueBadge from '$lib/components/SampleValueBadge/SampleValueBadge.svelte';
    import { hasValueBadge } from '$lib/components/SampleValueBadge/SampleValueBadge.helpers';
    import { useSettings } from '$lib/hooks/useSettings';
    import { SampleAnnotations, SampleImage } from '..';
    import type { SampleImageObjectFit } from '../SampleImage/types';

    const {
        sample,
        objectFit,
        tileWidth,
        tileHeight,
        displayTextOnImage
    }: {
        sample: ImageView;
        objectFit?: SampleImageObjectFit;
        tileWidth: number;
        tileHeight: number;
        displayTextOnImage?: string;
    } = $props();

    const { gridViewThumbnailQualityStore } = useSettings();
</script>

<SampleImage
    {sample}
    {objectFit}
    thumbnailQuality={$gridViewThumbnailQualityStore}
    thumbnailWidth={tileWidth}
    thumbnailHeight={tileHeight}
/>
<SampleClassificationPills
    {sample}
    hasBottomOverlay={Boolean(displayTextOnImage)}
    hasRightOverlay={hasValueBadge(sample.order_value, sample.similarity_score)}
/>
<SampleAnnotations {sample} {objectFit} outputWidth={tileWidth} outputHeight={tileHeight} />

<SampleValueBadge
    orderValue={sample.order_value}
    similarityScore={sample.similarity_score}
    hasBottomOverlay={Boolean(displayTextOnImage)}
/>
{#if displayTextOnImage}
    <div
        class="pointer-events-none absolute inset-x-0 bottom-0 z-10 rounded-b-lg bg-black/60 px-2 py-1 text-xs font-medium text-white"
    >
        <span class="block truncate" title={displayTextOnImage}>
            {displayTextOnImage}
        </span>
    </div>
{/if}
