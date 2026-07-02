<script lang="ts">
    import {
        SampleType,
        type AnnotationWithPayloadView,
        type ImageAnnotationView,
        type VideoFrameAnnotationView
    } from '$lib/api/lightly_studio_local';
    import { getSimilarityColor } from '$lib/utils';
    import AnnotationImageGridItem from '../AnnotationImageGridItem/AnnotationImageGridItem.svelte';
    import AnnotationVideoFrameGridItem from '../AnnotationVideoFrameGridItem/AnnotationVideoFrameGridItem.svelte';
    import type { CropWindow } from '../AnnotationItem/renderCropObjectUrl';

    type Props = {
        annotation: AnnotationWithPayloadView;
        width: number;
        height: number;
        cachedCollectionVersion: string;
        showLabel: boolean;
        selected?: boolean;
        onCropWindowChange?: (annotationId: string, window: CropWindow | null) => void;
    };

    let {
        annotation: annotationWithPayload,
        width,
        height,
        cachedCollectionVersion = '',
        showLabel = true,
        selected = false,
        onCropWindowChange
    }: Props = $props();
</script>

{#if annotationWithPayload.parent_sample_type == SampleType.IMAGE}
    <AnnotationImageGridItem
        annotation={annotationWithPayload.annotation}
        image={annotationWithPayload.parent_sample_data as ImageAnnotationView}
        containerWidth={width}
        containerHeight={height}
        {cachedCollectionVersion}
        {showLabel}
        {selected}
        {onCropWindowChange}
    />
{:else if annotationWithPayload.parent_sample_type == SampleType.VIDEO_FRAME || annotationWithPayload.parent_sample_type == SampleType.VIDEO}
    <AnnotationVideoFrameGridItem
        annotation={annotationWithPayload.annotation}
        videoFrame={annotationWithPayload.parent_sample_data as VideoFrameAnnotationView}
        containerWidth={width}
        containerHeight={height}
        {showLabel}
        {selected}
    />
{/if}

{#if annotationWithPayload.similarity_score !== undefined && annotationWithPayload.similarity_score !== null}
    <div
        class="absolute bottom-1 right-1 z-10 box-border flex h-5 items-center rounded bg-black/60 px-1.5 text-xs font-medium text-white backdrop-blur-sm"
    >
        <span
            class="mr-1.5 block h-2 w-2 rounded-full"
            style="background-color: {getSimilarityColor(annotationWithPayload.similarity_score)}"
        ></span>
        {annotationWithPayload.similarity_score.toFixed(2)}
    </div>
{/if}
