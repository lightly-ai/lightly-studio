<script lang="ts">
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useAnnotationClassVisibility } from '$lib/hooks';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { useSettings } from '$lib/hooks/useSettings';
    import { resolveEffectiveColorBySource } from '$lib/utils';
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
        objectFit = 'contain',
        outputWidth = sample.width,
        outputHeight = sample.height,
        isAnnotationVisible,
        colorMode
    }: {
        sample: SampleView;
        objectFit?: SampleImageObjectFit;
        outputWidth?: number;
        outputHeight?: number;
        /** The tree eyes. When set, they decide in place of the source filter and class eye. */
        isAnnotationVisible?: (annotation: AnnotationView) => boolean;
        /** The saved "Color by" mode. When set, it decides in place of the automatic rule. */
        colorMode?: 'class' | 'source';
    } = $props();

    const { isHidden } = useHideAnnotations();
    const { hiddenClassNamesStore } = useAnnotationClassVisibility();
    const { showBoundingBoxesForSegmentationStore, enforceColoringByClassStore } = useSettings();
    const { isSourceVisible, multipleSourcesVisible, collectionIdToName } =
        useAnnotationCollectionsFilter();

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
        const sourceIsVisible = $isSourceVisible;
        const idToName = $collectionIdToName;
        const hiddenClasses = $hiddenClassNamesStore;
        const isVisible =
            isAnnotationVisible ??
            ((annotation: AnnotationView) =>
                sourceIsVisible(annotation.annotation_collection_id) &&
                !hiddenClasses.includes(annotation.annotation_label.annotation_label_name));
        const colorBySource = resolveEffectiveColorBySource({
            multipleSourcesVisible: $multipleSourcesVisible,
            enforceColoringByClass: $enforceColoringByClassStore,
            colorMode
        });

        return sample.annotations
            .filter(isVisible)
            .filter((annotation) => annotation.annotation_type !== 'classification')
            .map((annotation) => {
                const canvas = mapToCanvasAnnotation(
                    annotation,
                    showInstanceSegmentationBoundingBoxes
                );
                if (!canvas) return null;
                if (colorBySource) {
                    const collectionName = idToName[annotation.annotation_collection_id];
                    if (collectionName) {
                        return { ...canvas, sourceName: collectionName };
                    }
                }
                return canvas;
            })
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
            sourceWidth={sample.width}
            sourceHeight={sample.height}
            {outputWidth}
            {outputHeight}
            {objectFit}
            annotations={annotationsWithVisuals}
            alpha={0.8}
            className={`pointer-events-none absolute inset-0 z-[1] h-full w-full ${objectFitClass}`}
        />
    </div>
{/if}
