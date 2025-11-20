<script lang="ts">
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { type ComponentProps } from 'svelte';
    import SampleAnnotation from '../SampleAnnotation/SampleAnnotation.svelte';
    import type { SampleImageObjectFit } from '../SampleImage/types';
    import type { AnnotationView, SampleView, VideoFrameView } from '$lib/api/lightly_studio_local';

    const {
        sample,
        size,
        sampleImageObjectFit = 'contain',
        showLabel
    }: {
        sample: VideoFrameView;
        size: number;
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
    style="position: absolute; top: 0; left: 0;"
    viewBox={`0 0 ${sample.video.width} ${sample.video.height}`}
    preserveAspectRatio={sampleImageObjectFit === 'contain' ? 'xMidYMid meet' : 'xMidYMid slice'}
    width={size}
    height={size}
>
    <g class:invisible={$isHidden}>
        {#each annotationsWithVisuals as annotation (annotation.annotation_id)}
            <SampleAnnotation {annotation} {showLabel} imageWidth={sample.video.width} />
        {/each}
    </g>
</svg>
