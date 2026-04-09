<script lang="ts">
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useSettings } from '$lib/hooks/useSettings';
    import { type ComponentProps } from 'svelte';
    import SampleAnnotation from '../SampleAnnotation/SampleAnnotation.svelte';
    import type { SampleImageObjectFit } from '../SampleImage/types';
    import type {
        AnnotationView,
        FrameView,
        SampleView,
        VideoFrameView
    } from '$lib/api/lightly_studio_local';
    import { shouldShowBoundingBoxForAnnotation } from '$lib/utils/shouldShowBoundingBoxForAnnotation';
    import { SampleAnnotations } from '..';

    export interface PrerenderedAnnotation {
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

    const { isHidden } = useHideAnnotations();
    const { showBoundingBoxesForSegmentationStore } = useSettings();
    const annotations: AnnotationView[] = $derived((sample.sample as SampleView).annotations ?? []);
    const annotationsWithVisuals = $derived(
        annotations.filter((annotation) => annotation.annotation_type !== 'classification')
    );

    // Filter out segmentation annotations if we have prerendered versions
    const annotationsToRender = $derived(
        prerenderedAnnotations && prerenderedAnnotations.length > 0
            ? annotationsWithVisuals.filter(
                  (annotation) => annotation.annotation_type !== 'instance_segmentation'
              )
            : annotationsWithVisuals
    );
</script>

{#if !showLabel}
    <SampleAnnotations
        sample={{
            width: sampleWidth,
            height: sampleHeight,
            annotations: annotations
        }}
        objectFit={sampleImageObjectFit}
    />
{:else}
    <svg
        style="position: absolute; top: 0; left: 0; pointer-events: none"
        viewBox={`0 0 ${sampleWidth} ${sampleHeight}`}
        preserveAspectRatio={sampleImageObjectFit === 'contain'
            ? 'xMidYMid meet'
            : 'xMidYMid slice'}
        {width}
        {height}
    >
        <g class="sample-annotation" class:invisible={$isHidden}>
            <!-- Render prerendered segmentation masks first -->
            {#if prerenderedAnnotations}
                {#each prerenderedAnnotations as prerendered, index (index)}
                    <image
                        href={prerendered.dataUrl}
                        x="0"
                        y="0"
                        width={prerendered.width}
                        height={prerendered.height}
                        opacity={prerendered.opacity ?? 0.65}
                        pointer-events="none"
                    />
                {/each}
            {/if}

            <!-- Render other annotations (bounding boxes, labels, etc.) -->
            {#each annotationsToRender as annotation (annotation.sample_id)}
                <SampleAnnotation
                    {annotation}
                    {showLabel}
                    showBoundingBox={shouldShowBoundingBoxForAnnotation(
                        annotation,
                        $showBoundingBoxesForSegmentationStore
                    )}
                    imageWidth={sampleWidth}
                />
            {/each}
        </g>
    </svg>
{/if}
