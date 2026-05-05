<script lang="ts">
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useSettings } from '$lib/hooks/useSettings';
    import { onMount, type ComponentProps } from 'svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { AnnotationCanvas } from '$lib/components';
    import type { SampleImageObjectFit } from '../SampleImage/types';

    type AnnotationCanvasAnnotation = NonNullable<
        ComponentProps<typeof AnnotationCanvas>['annotations']
    >[number];

    type SampleView = {
        sample_id: string;
        width: number;
        height: number;
        annotations: AnnotationView[];
    };

    const {
        sample,
        objectFit = 'contain'
    }: {
        sample: SampleView;
        objectFit?: SampleImageObjectFit;
    } = $props();

    const { isHidden } = useHideAnnotations();
    const { showBoundingBoxesForSegmentationStore } = useSettings();

    // Normalize backend annotation variants into the smaller canvas render contract.
    const mapToCanvasAnnotation = (
        annotation: SampleView['annotations'][number],
        showInstanceSegmentationBoundingBoxes: boolean
    ): AnnotationCanvasAnnotation | null => {
        const annotation_label_name = annotation.annotation_label.annotation_label_name;

        if (
            annotation.annotation_type === 'object_detection' &&
            annotation.object_detection_details
        ) {
            return {
                annotation_type: 'object_detection',
                annotation_label_name,
                object_detection_details: annotation.object_detection_details
            } satisfies AnnotationCanvasAnnotation;
        }

        if (annotation.annotation_type === 'segmentation_mask' && annotation.segmentation_details) {
            const { x, y, width, height, segmentation_mask } = annotation.segmentation_details;
            return {
                annotation_type: 'segmentation_mask',
                annotation_label_name,
                segmentation_mask: segmentation_mask ?? [],
                object_detection_details: showInstanceSegmentationBoundingBoxes
                    ? { x, y, width, height }
                    : undefined
            } satisfies AnnotationCanvasAnnotation;
        }

        return null;
    };

    const annotationsWithVisuals: AnnotationCanvasAnnotation[] = $derived.by(() => {
        const showInstanceSegmentationBoundingBoxes = $showBoundingBoxesForSegmentationStore;

        return sample.annotations
            .filter((annotation) => annotation.annotation_type !== 'classification')
            .map((annotation) =>
                mapToCanvasAnnotation(annotation, showInstanceSegmentationBoundingBoxes)
            )
            .filter((annotation): annotation is AnnotationCanvasAnnotation => annotation != null);
    });
    const objectFitClass = $derived(objectFit === 'cover' ? 'object-cover' : 'object-contain');

    let showAnnotations = $state(false);

    // Delay canvas mount work until the browser is idle to reduce scroll/jank on large lists.
    const idle = window.requestIdleCallback ?? ((cb) => setTimeout(cb, 10));

    onMount(() => {
        idle(() => {
            showAnnotations = true;
        });
    });
</script>

{#if showAnnotations && !$isHidden && annotationsWithVisuals.length > 0}
    <div data-testid="sample-annotation-item">
        <AnnotationCanvas
            sampleId={sample.sample_id}
            width={sample.width}
            height={sample.height}
            annotations={annotationsWithVisuals}
            alpha={0.8}
            className={`pointer-events-none absolute inset-0 z-[1] h-full w-full ${objectFitClass}`}
        />
    </div>
{/if}
