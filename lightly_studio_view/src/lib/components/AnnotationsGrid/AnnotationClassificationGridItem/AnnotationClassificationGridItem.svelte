<script lang="ts">
    import {
        SampleType,
        type ImageAnnotationView,
        type VideoFrameAnnotationView
    } from '$lib/api/lightly_studio_local';
    import SampleClassificationPills from '$lib/components/SampleClassificationPills/SampleClassificationPills.svelte';
    import { SelectableBox } from '$lib/components';
    import { useSettings } from '$lib/hooks/useSettings';
    import { getGridFrameURL, getGridImageURL, getGridThumbnailRequestSize } from '$lib/utils';
    import type { ClassificationTile } from '../groupClassificationsBySample';

    interface Props {
        tile: ClassificationTile;
        containerWidth: number;
        containerHeight: number;
        selected?: boolean;
        /** Collection version cache-buster for image thumbnails. */
        cachedCollectionVersion?: string;
    }

    let {
        tile,
        containerWidth,
        containerHeight,
        selected = false,
        cachedCollectionVersion = ''
    }: Props = $props();

    const { gridViewThumbnailQualityStore } = useSettings();

    function getThumbnailUrl(): string {
        const renderedWidth = getGridThumbnailRequestSize(
            containerWidth,
            globalThis.window?.devicePixelRatio || 1
        );
        const renderedHeight = getGridThumbnailRequestSize(
            containerHeight,
            globalThis.window?.devicePixelRatio || 1
        );

        if (tile.representative.parent_sample_type === SampleType.IMAGE) {
            const image = tile.representative.parent_sample_data as ImageAnnotationView;
            return getGridImageURL({
                sampleId: image.sample_id,
                quality: $gridViewThumbnailQualityStore,
                renderedWidth,
                renderedHeight,
                cacheBuster: cachedCollectionVersion
            });
        }

        const videoFrame = tile.representative.parent_sample_data as VideoFrameAnnotationView;
        return getGridFrameURL({
            sampleId: videoFrame.sample_id,
            quality: $gridViewThumbnailQualityStore,
            renderedWidth,
            renderedHeight
        });
    }

    const annotations = $derived(tile.allAnnotations.map((annotation) => annotation.annotation));
    const thumbnailStyle = $derived(
        `width: ${containerWidth}px; height: ${containerHeight}px; background-image: url("${getThumbnailUrl()}"); background-position: center; background-size: contain; background-repeat: no-repeat;`
    );
</script>

<div
    class="relative h-full w-full rounded-lg bg-black"
    class:grid-item-selected={selected}
    style={thumbnailStyle}
    data-testid="classification-grid-item"
>
    {#if selected}
        <div class="pointer-events-none absolute right-2 top-1.5 z-10" inert>
            <SelectableBox onSelect={() => undefined} isSelected={true} />
        </div>
    {/if}

    <!-- Classification tiles aggregate multiple label annotations onto a single sample thumbnail. -->
    <SampleClassificationPills sample={{ annotations }} />
</div>
