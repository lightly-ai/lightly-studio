<script lang="ts">
    import { untrack } from 'svelte';
    import { type AnnotationWithPayloadView } from '$lib/api/lightly_studio_local';
    import { useSettings } from '$lib/hooks';
    import SampleClassificationPills from '$lib/components/SampleClassificationPills/SampleClassificationPills.svelte';
    import { getThumbnailUrl, getSampleDimensions } from './getThumbnailData';
    import type { CropWindow } from '../AnnotationItem/renderCropObjectUrl';
    import { resolveImageMediaSource } from '$lib/utils';

    interface Props {
        /** The classification annotation with its parent sample data. */
        annotation: AnnotationWithPayloadView;
        /** Width of the grid container tile in pixels. */
        containerWidth: number;
        /** Height of the grid container tile in pixels. */
        containerHeight: number;
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
        selected = false,
        cachedCollectionVersion = '',
        onCropWindowChange
    }: Props = $props();

    const { gridViewThumbnailQualityStore } = useSettings();

    // Stable id captured at init — same pattern as AnnotationItem (avoids re-reading
    // the annotation prop during effect cleanup after the grid array shrinks).
    const annotationId = untrack(() => annotation.annotation.sample_id);

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
    let backgroundUrl = $state('');
    const backgroundImage = $derived(backgroundUrl ? `url("${backgroundUrl}")` : 'none');

    $effect(() => {
        const sourceUrl = thumbnailUrl;
        const controller = new AbortController();
        backgroundUrl = '';
        void resolveImageMediaSource(sourceUrl, controller.signal).then((resolvedUrl) => {
            if (!controller.signal.aborted) backgroundUrl = resolvedUrl ?? '';
        });
        return () => controller.abort();
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
    style="width: {containerWidth}px; height: {containerHeight}px; background-image: {backgroundImage}; background-size: cover; background-position: center;"
>
    <SampleClassificationPills sample={{ annotations: [annotation.annotation] }} showAllSources />
</div>
