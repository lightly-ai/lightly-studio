<script lang="ts">
    import {
        SampleType,
        type AnnotationWithPayloadView,
        type ImageAnnotationView,
        type VideoFrameAnnotationView
    } from '$lib/api/lightly_studio_local';
    import { get } from 'svelte/store';
    import { useSettings } from '$lib/hooks/useSettings';
    import SampleClassificationPills from '$lib/components/SampleClassificationPills/SampleClassificationPills.svelte';
    import { getGridImageURL, getGridFrameURL, getGridThumbnailRequestSize } from '$lib/utils';
    import type { CropWindow } from '../AnnotationItem/renderCropObjectUrl';

    interface Props {
        /** The classification annotation with its parent sample data. */
        annotation: AnnotationWithPayloadView;
        /** Width of the grid container tile in pixels. */
        containerWidth: number;
        /** Height of the grid container tile in pixels. */
        containerHeight: number;
        /** Whether text labels are visible globally. */
        showLabel: boolean;
        /** Whether this tile is currently selected. */
        selected?: boolean;
        /** Collection version cache-buster (same as AnnotationImageGridItem). */
        cachedCollectionVersion?: string;
        /** Reports full-image crop geometry for drag-to-search (same contract as AnnotationItem). */
        onCropWindowChange?: (annotationId: string, window: CropWindow | null) => void;
    }

    let {
        annotation,
        containerWidth,
        containerHeight,
        showLabel,
        selected = false,
        cachedCollectionVersion = '',
        onCropWindowChange
    }: Props = $props();

    const { gridViewThumbnailQualityStore } = useSettings();

    let quality = $state(get(gridViewThumbnailQualityStore));
    $effect(() => gridViewThumbnailQualityStore.subscribe((v) => (quality = v)));

    // Stable id captured at init — same pattern as AnnotationItem (avoids re-reading
    // the annotation prop during effect cleanup after the grid array shrinks).
    const annotationId = annotation.annotation.sample_id;

    const thumbnailUrl = $derived.by(() => {
        const dpr = globalThis.window?.devicePixelRatio || 1;
        const renderedWidth = getGridThumbnailRequestSize(containerWidth, dpr);
        const renderedHeight = getGridThumbnailRequestSize(containerHeight, dpr);
        if (annotation.parent_sample_type === SampleType.IMAGE) {
            const image = annotation.parent_sample_data as ImageAnnotationView;
            return getGridImageURL({
                sampleId: image.sample_id,
                quality,
                renderedWidth,
                renderedHeight,
                cacheBuster: cachedCollectionVersion
            });
        }
        const frame = annotation.parent_sample_data as VideoFrameAnnotationView;
        return getGridFrameURL({
            sampleId: frame.sample_id,
            quality,
            renderedWidth,
            renderedHeight
        });
    });

    const sampleDimensions = $derived.by(() => {
        if (annotation.parent_sample_type === SampleType.IMAGE) {
            const image = annotation.parent_sample_data as ImageAnnotationView;
            return { width: image.width, height: image.height };
        }
        const frame = annotation.parent_sample_data as VideoFrameAnnotationView;
        return { width: frame.video.width, height: frame.video.height };
    });

    // Emit a full-image CropWindow so classification tiles participate in drag-to-search.
    // windowX/Y=0 covers the entire sample — there is no bounding box to crop for classification.
    $effect(() => {
        if (!thumbnailUrl) return;
        onCropWindowChange?.(annotationId, {
            sourceUrl: thumbnailUrl,
            sampleWidth: sampleDimensions.width,
            sampleHeight: sampleDimensions.height,
            windowWidth: sampleDimensions.width,
            windowHeight: sampleDimensions.height,
            windowX: 0,
            windowY: 0
        });
        return () => onCropWindowChange?.(annotationId, null);
    });
</script>

<div
    class="relative overflow-hidden rounded-lg bg-black"
    class:grid-item-selected={selected}
    aria-selected={selected}
    style="width: {containerWidth}px; height: {containerHeight}px; background-image: url('{thumbnailUrl}'); background-size: cover; background-position: center;"
>
    {#if showLabel}
        <!-- One tile shows exactly one label — [annotation.annotation] wraps a single classification. -->
        <SampleClassificationPills sample={{ annotations: [annotation.annotation] }} />
    {/if}
</div>
