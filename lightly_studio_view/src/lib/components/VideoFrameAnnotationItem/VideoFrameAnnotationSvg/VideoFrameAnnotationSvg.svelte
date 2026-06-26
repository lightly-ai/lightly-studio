<script lang="ts">
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useAnnotationClassVisibility, useSettings } from '$lib/hooks';
    import { type ComponentProps } from 'svelte';
    import { SampleAnnotation } from '$lib/components';
    import type { SampleImageObjectFit } from '../../SampleImage/types';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { shouldShowBoundingBoxForAnnotation } from '$lib/utils/shouldShowBoundingBoxForAnnotation';
    import type { PrerenderedAnnotation } from '../VideoFrameAnnotationItem.svelte';

    interface Props {
        /** Annotations for the current frame. */
        annotations: AnnotationView[];
        /** Pre-rendered mask image data keyed by annotation ID, used to avoid re-rendering heavy segmentation masks. */
        prerenderedAnnotations?: PrerenderedAnnotation[];
        /** Rendered width of the SVG overlay in pixels. */
        width: number;
        /** Rendered height of the SVG overlay in pixels. */
        height: number;
        /** Original width of the source sample in pixels, used for the SVG viewBox. */
        sampleWidth: number;
        /** Original height of the source sample in pixels, used for the SVG viewBox. */
        sampleHeight: number;
        /** How the underlying image is fitted, controls SVG preserveAspectRatio. */
        sampleImageObjectFit?: SampleImageObjectFit;
        /** Controls whether annotation labels are rendered alongside bounding boxes. */
        showLabel?: ComponentProps<typeof SampleAnnotation>['showLabel'];
    }

    const {
        annotations,
        prerenderedAnnotations,
        width,
        height,
        sampleWidth,
        sampleHeight,
        sampleImageObjectFit = 'contain',
        showLabel
    }: Props = $props();

    const { isHidden } = useHideAnnotations();
    const { hiddenClassNamesStore } = useAnnotationClassVisibility();
    const { showBoundingBoxesForSegmentationStore } = useSettings();

    const annotationsWithVisuals = $derived(
        annotations
            .filter((annotation) => annotation.annotation_type !== 'classification')
            .filter(
                (annotation) =>
                    !$hiddenClassNamesStore.includes(
                        annotation.annotation_label.annotation_label_name
                    )
            )
    );

    const prerenderedMap = $derived.by(() => {
        if (!prerenderedAnnotations) return new Map();
        return new Map(
            prerenderedAnnotations.map((prerendered) => [prerendered.annotationId, prerendered])
        );
    });
</script>

<svg
    style="position: absolute; top: 0; left: 0; pointer-events: none"
    viewBox={`0 0 ${sampleWidth} ${sampleHeight}`}
    preserveAspectRatio={sampleImageObjectFit === 'contain' ? 'xMidYMid meet' : 'xMidYMid slice'}
    {width}
    {height}
>
    <g class="sample-annotation" class:invisible={$isHidden}>
        <!-- Render all annotations with prerendered data when available -->
        {#each annotationsWithVisuals as annotation (annotation.sample_id)}
            {@const prerendered = prerenderedMap.get(annotation.sample_id)}
            <SampleAnnotation
                {annotation}
                {showLabel}
                showBoundingBox={shouldShowBoundingBoxForAnnotation(
                    annotation,
                    $showBoundingBoxesForSegmentationStore
                )}
                imageWidth={sampleWidth}
                prerenderedDataUrl={prerendered?.dataUrl}
                prerenderedHeight={prerendered?.height}
            />
        {/each}
    </g>
</svg>
