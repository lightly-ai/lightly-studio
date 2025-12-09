<script lang="ts">
    import {
        SampleType,
        type AnnotationWithPayloadView,
        type ImageAnnotationView,
        type VideoFrameAnnotationView
    } from '$lib/api/lightly_studio_local';
    import AnnotationImageGridItem from '../AnnotationImageGridItem/AnnotationImageGridItem.svelte';
    import AnnotationVideoFrameGridItem from '../AnnotationVideoFrameGridItem/AnnotationVideoFrameGridItem.svelte';

    type Props = {
        annotation: AnnotationWithPayloadView;
        width: number;
        height: number;
        cachedDatasetVersion: string;
        showLabel: boolean;
        sampleType: SampleType;
        selected?: boolean;
    };

    let {
        annotation: annotationWithPayload,
        width,
        height,
        sampleType,
        cachedDatasetVersion = '',
        showLabel = true,
        selected = false
    }: Props = $props();
</script>

{#if sampleType == SampleType.IMAGE}
    <AnnotationImageGridItem
        annotation={annotationWithPayload.annotation}
        image={annotationWithPayload.parent_sample_data as ImageAnnotationView}
        containerWidth={width}
        containerHeight={height}
        {cachedDatasetVersion}
        {showLabel}
        {selected}
    />
{:else if sampleType == SampleType.VIDEO_FRAME || sampleType == SampleType.VIDEO}
    <AnnotationVideoFrameGridItem
        annotation={annotationWithPayload.annotation}
        videoFrame={annotationWithPayload.parent_sample_data as VideoFrameAnnotationView}
        containerWidth={width}
        containerHeight={height}
        {showLabel}
        {selected}
    />
{/if}
