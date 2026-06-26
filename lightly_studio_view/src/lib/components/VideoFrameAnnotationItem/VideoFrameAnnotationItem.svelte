<script lang="ts">
    import { type ComponentProps } from 'svelte';
    import SampleAnnotation from '../SampleAnnotation/SampleAnnotation.svelte';
    import type { SampleImageObjectFit } from '../SampleImage/types';
    import type {
        AnnotationView,
        FrameView,
        SampleView,
        VideoFrameView
    } from '$lib/api/lightly_studio_local';
    import { SampleAnnotations } from '..';
    import VideoFrameAnnotationSvg from './VideoFrameAnnotationSvg/VideoFrameAnnotationSvg.svelte';

    export interface PrerenderedAnnotation {
        frameId: string;
        annotationId: string;
        dataUrl: string;
        width: number;
        height: number;
        opacity?: number;
    }

    const {
        sample,
        width,
        height,
        sampleImageObjectFit = 'contain',
        showLabel,
        sampleWidth,
        sampleHeight,
        prerenderedAnnotations
    }: {
        sample: VideoFrameView | FrameView;
        width: number;
        height: number;
        sampleWidth: number;
        sampleHeight: number;
        sampleImageObjectFit?: SampleImageObjectFit;
        showLabel?: ComponentProps<typeof SampleAnnotation>['showLabel'];
        prerenderedAnnotations?: PrerenderedAnnotation[];
    } = $props();

    const annotations: AnnotationView[] = $derived((sample.sample as SampleView).annotations ?? []);
</script>

{#if !showLabel}
    <!-- Label-free mode uses the shared canvas renderer for better performance with many masks. -->
    <SampleAnnotations
        sample={{
            sample_id: sample.sample_id,
            width: sampleWidth,
            height: sampleHeight,
            annotations: annotations
        }}
        objectFit={sampleImageObjectFit}
    />
{:else}
    <VideoFrameAnnotationSvg
        {annotations}
        {prerenderedAnnotations}
        {width}
        {height}
        {sampleWidth}
        {sampleHeight}
        {sampleImageObjectFit}
        {showLabel}
    />
{/if}
