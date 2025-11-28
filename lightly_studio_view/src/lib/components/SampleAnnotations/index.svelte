<script lang="ts">
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { type ComponentProps } from 'svelte';
    import SampleAnnotation from '../SampleAnnotation/SampleAnnotation.svelte';
    import type { SampleImageObjectFit } from '../SampleImage/types';
    import type { ImageView } from '$lib/api/lightly_studio_local';

    const {
        sample,
        containerWidth,
        containerHeight,
        sampleImageObjectFit = 'contain',
        showLabel
    }: {
        sample: ImageView;
        containerWidth: number;
        containerHeight: number;
        sampleImageObjectFit?: SampleImageObjectFit;
        showLabel?: ComponentProps<typeof SampleAnnotation>['showLabel'];
    } = $props();

    const { isHidden } = useHideAnnotations();
    const annotationsWithVisuals = $derived(
        sample.annotations.filter((annotation) => annotation.annotation_type !== 'classification')
    );
</script>

<svg
    style="position: absolute; top: 0; left: 0;"
    viewBox={`0 0 ${sample.width} ${sample.height}`}
    preserveAspectRatio={sampleImageObjectFit === 'contain' ? 'xMidYMid meet' : 'xMidYMid slice'}
    width={containerWidth}
    height={containerHeight}
>
    <g class:invisible={$isHidden}>
        {#each annotationsWithVisuals as annotation (annotation.sample_id)}
            <SampleAnnotation {annotation} {showLabel} imageWidth={sample.width} />
        {/each}
    </g>
</svg>
