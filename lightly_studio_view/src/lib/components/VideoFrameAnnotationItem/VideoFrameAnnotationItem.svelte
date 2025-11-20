<script lang="ts">
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { type ComponentProps } from 'svelte';
    import SampleAnnotation from '../SampleAnnotation/SampleAnnotation.svelte';
    import type { SampleImageObjectFit } from '../SampleImage/types';
    import type {
        AnnotationView,
        FrameView,
        SampleView,
        VideoFrameView
    } from '$lib/api/lightly_studio_local';

    const {
        sample,
        width,
        height,
        sampleImageObjectFit = 'contain',
        showLabel,
        sampleWidth,
        sampleHeight
    }: {
        sample: VideoFrameView | FrameView;
        width: number;
        height: number;
        sampleWidth: number;
        sampleHeight: number;
        sampleImageObjectFit?: SampleImageObjectFit;
        showLabel?: ComponentProps<typeof SampleAnnotation>['showLabel'];
    } = $props();

    const { isHidden } = useHideAnnotations();
    const annotations: AnnotationView[] = $derived((sample.sample as SampleView).annotations ?? []);
    const annotationsWithVisuals = $derived(
        annotations.filter((annotation) => annotation.annotation_type !== 'classification')
    );
</script>

<svg
    style="position: absolute; top: 0; left: 0; pointer-events: none"
    viewBox={`0 0 ${sampleWidth} ${sampleHeight}`}
    preserveAspectRatio={sampleImageObjectFit === 'contain' ? 'xMidYMid meet' : 'xMidYMid slice'}
    {width}
    {height}
>
    <g class:invisible={$isHidden}>
        {#each annotationsWithVisuals as annotation (annotation.annotation_id)}
            <SampleAnnotation {annotation} {showLabel} imageWidth={sampleWidth} />
        {/each}
    </g>
</svg>
