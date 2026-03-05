<script lang="ts">
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { onMount, type ComponentProps } from 'svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { AnnotationCanvas } from '$lib/components';

    type AnnotationCanvasAnnotation = NonNullable<
        ComponentProps<typeof AnnotationCanvas>['annotations']
    >[number];

    type SampleView = {
        width: number;
        height: number;
        annotations: AnnotationView[];
    };

    const {
        sample
    }: {
        sample: SampleView;
    } = $props();

    const { isHidden } = useHideAnnotations();

    const mapToCanvasAnnotation = (
        annotation: SampleView['annotations'][number]
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

        if (annotation.annotation_type === 'semantic_segmentation') {
            return {
                annotation_type: 'semantic_segmentation',
                annotation_label_name,
                segmentation_mask: annotation.segmentation_details?.segmentation_mask ?? []
            } satisfies AnnotationCanvasAnnotation;
        }

        if (
            annotation.annotation_type === 'instance_segmentation' &&
            annotation.segmentation_details
        ) {
            const { x, y, width, height, segmentation_mask } = annotation.segmentation_details;
            return {
                annotation_type: 'instance_segmentation',
                annotation_label_name,
                segmentation_mask: segmentation_mask ?? [],
                object_detection_details: { x, y, width, height }
            } satisfies AnnotationCanvasAnnotation;
        }

        return null;
    };

    const annotationsWithVisuals: AnnotationCanvasAnnotation[] = $derived(
        sample.annotations
            .filter((annotation) => annotation.annotation_type !== 'classification')
            .map(mapToCanvasAnnotation)
            .filter((annotation): annotation is AnnotationCanvasAnnotation => annotation != null)
    );

    let showAnnotations = $state(false);

    const idle = window.requestIdleCallback ?? ((cb) => setTimeout(cb, 10));

    onMount(() => {
        idle(() => {
            showAnnotations = true;
        });
    });
</script>

{#if showAnnotations && !$isHidden}
    <AnnotationCanvas
        width={sample.width}
        height={sample.height}
        annotations={annotationsWithVisuals}
        alpha={0.8}
        className="pointer-events-none absolute w-full object-contain h-full inset-0 z-10"
    />
{/if}
