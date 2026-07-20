<script lang="ts">
    import { type AnnotationWithPayloadView } from '$lib/api/lightly_studio_local';
    import { useSettings } from '$lib/hooks';
    import SampleClassificationPills from '$lib/components/SampleClassificationPills/SampleClassificationPills.svelte';
    import { getThumbnailUrl, getSampleDimensions } from './getThumbnailData';
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

    // Stable id captured at init — same pattern as AnnotationItem (avoids re-reading
    // the annotation prop during effect cleanup after the grid array shrinks).
    const annotationId = annotation.annotation.sample_id;

    const thumbnailUrl = $derived(
        getThumbnailUrl({
            annotation,
            quality: $gridViewThumbnailQualityStore,
            containerWidth,
            containerHeight,
            cachedCollectionVersion
        })
    );

    const sampleDimensions = $derived(getSampleDimensions(annotation));

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
