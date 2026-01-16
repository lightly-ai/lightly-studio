<script lang="ts">
    import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
    import { ZoomableContainer } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { afterNavigate } from '$app/navigation';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import SampleDetailsAnnotation from '../SampleDetailsAnnotation/SampleDetailsAnnotation.svelte';
    import SampleEraserRect from '../SampleEraserRect/SampleEraserRect.svelte';
    import SampleInstanceSegmentationRect from '../SampleInstanceSegmentationRect/SampleInstanceSegmentationRect.svelte';
    import SampleObjectDetectionRect from '../SampleObjectDetectionRect/SampleObjectDetectionRect.svelte';
    import { select } from 'd3-selection';
    import { getColorByLabel } from '$lib/utils';
    import _ from 'lodash';
    import BrushToolPopUp from '../BrushToolPopUp/BrushToolPopUp.svelte';
    import SampleDetailsToolbar from '../SampleDetailsToolbar/SampleDetailsToolbar.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';

    type SampleDetailsImageContainerProps = {
        sample: {
            width: number;
            height: number;
            annotations: AnnotationView[];
            sampleId: string;
        };
        collectionId: string;
        imageUrl: string;
        hideAnnotationsIds: Set<string>;
        isResizable: boolean;
        isEraser: boolean;
        selectedAnnotationId: string | null | undefined;
        annotationLabel?: string | null | undefined;
        brushRadius: number;
        annotationType: string | null | undefined;
        refetch: () => void;
        toggleAnnotationSelection: (sampleId: string) => void;
    };

    let {
        sample,
        imageUrl,
        hideAnnotationsIds,
        collectionId,
        isResizable,
        toggleAnnotationSelection,
        selectedAnnotationId = $bindable<string>(),
        annotationLabel,
        isEraser,
        refetch,
        brushRadius,
        annotationType
    }: SampleDetailsImageContainerProps = $props();

    const { isEditingMode, imageBrightness, imageContrast } = useGlobalStorage();
    const { isHidden } = useHideAnnotations();

    let resetZoomTransform: (() => void) | undefined = $state();
    let mousePosition = $state<{ x: number; y: number } | null>(null);
    let interactionRect: SVGRectElement | null = $state(null);

    let sampleId = $derived(sample.sampleId);
    const actualAnnotationsToShow = $derived.by(() => {
        return sample.annotations.filter(
            (annotation) => !hideAnnotationsIds.has(annotation.sample_id)
        );
    });
    const drawerStrokeColor = $derived(
        annotationLabel !== 'default' && annotationLabel
            ? getColorByLabel(annotationLabel, 1).color
            : 'rgb(0, 0, 255)'
    );

    $effect(() => {
        setupMouseMonitor();

        if (!$isEditingMode) {
            setIsErasing(false);
            setIsDrawing(false);
        }
    });

    const setupMouseMonitor = () => {
        if (!interactionRect) return;

        const rectSelection = select(interactionRect);

        rectSelection.on('mousemove', trackMousePosition);
    };

    const trackMousePositionOrig = (event: MouseEvent) => {
        if (!interactionRect) return;

        const svgRect = interactionRect.getBoundingClientRect();
        const clientX = event.clientX;
        const clientY = event.clientY;
        const x = ((clientX - svgRect.left) / svgRect.width) * sample.width;
        const y = ((clientY - svgRect.top) / svgRect.height) * sample.height;

        mousePosition = { x, y };
        event.stopPropagation();
        event.preventDefault();
    };

    const trackMousePosition = _.throttle(trackMousePositionOrig, 50);

    afterNavigate(() => {
        // Reset zoom transform when navigating to new sample
        resetZoomTransform?.();
    });

    function determineHighlightForAnnotation(annotationId: string) {
        if (annotationLabelContext.isDrawing || annotationLabelContext.isDragging)
            return 'disabled';

        if (!selectedAnnotationId) return 'auto';

        if (selectedAnnotationId === annotationId) return 'active';

        return 'disabled';
    }
    const {
        context: annotationLabelContext,
        setIsErasing,
        setIsDrawing
    } = useAnnotationLabelContext();
    const { context: sampleDetailsToolbarContext } = useSampleDetailsToolbarContext();
</script>

<ZoomableContainer
    width={sample.width}
    height={sample.height}
    panEnabled={!(annotationLabelContext.isDrawing || annotationLabelContext.isErasing)}
    cursor={'grab'}
    registerResetFn={(fn) => (resetZoomTransform = fn)}
>
    {#snippet toolbarContent()}
        {#if $isEditingMode}
            <SampleDetailsToolbar />
        {/if}
    {/snippet}
    {#snippet zoomPanelContent()}
        {#if annotationType == AnnotationType.INSTANCE_SEGMENTATION && $isEditingMode}
            <BrushToolPopUp />
        {/if}
    {/snippet}
    {#snippet zoomableContent()}
        <image
            href={imageUrl}
            style={`filter: brightness(${$imageBrightness}) contrast(${$imageContrast})`}
        />

        <g class:invisible={$isHidden}>
            {#each actualAnnotationsToShow as annotation (annotation.sample_id)}
                <!-- The SampleInstanceSegmentationRect or SampleEraserRect component will render the preview while drawing a segmentation mask-->
                <g
                    class:hidden={annotationLabelContext.isDrawing &&
                        annotation.sample_id === annotationLabelContext.annotationId}
                >
                    <SampleDetailsAnnotation
                        annotationId={annotation.sample_id}
                        {sampleId}
                        {collectionId}
                        {isResizable}
                        {toggleAnnotationSelection}
                        {sample}
                        highlight={annotationLabelContext.isDragging
                            ? 'disabled'
                            : determineHighlightForAnnotation(annotation.sample_id)}
                    />
                </g>
            {/each}
            {#if mousePosition && $isEditingMode && (sampleDetailsToolbarContext.status === 'brush' || sampleDetailsToolbarContext.status === 'bounding-box')}
                <!-- Horizontal crosshair line -->
                <line
                    x1="0"
                    y1={mousePosition.y}
                    x2={sample.width}
                    y2={mousePosition.y}
                    stroke={drawerStrokeColor}
                    stroke-width="1"
                    vector-effect="non-scaling-stroke"
                    stroke-dasharray="5,5"
                    opacity="0.6"
                />
                <!-- Vertical crosshair line -->
                <line
                    x1={mousePosition.x}
                    y1="0"
                    x2={mousePosition.x}
                    y2={sample.height}
                    stroke={drawerStrokeColor}
                    stroke-width="1"
                    stroke-dasharray="5,5"
                    opacity="0.6"
                />
            {/if}
        </g>
        {#if $isEditingMode}
            {#if isEraser}
                <SampleEraserRect
                    bind:interactionRect
                    {collectionId}
                    {brushRadius}
                    {refetch}
                    {sample}
                    {mousePosition}
                    {drawerStrokeColor}
                />
            {:else if annotationType == AnnotationType.INSTANCE_SEGMENTATION}
                <SampleInstanceSegmentationRect
                    bind:interactionRect
                    {mousePosition}
                    {sampleId}
                    {collectionId}
                    {brushRadius}
                    {refetch}
                    {drawerStrokeColor}
                    {annotationLabel}
                    {sample}
                />
            {:else if annotationType == AnnotationType.OBJECT_DETECTION}
                <SampleObjectDetectionRect
                    bind:interactionRect
                    {sample}
                    {sampleId}
                    {collectionId}
                    {drawerStrokeColor}
                    {refetch}
                />
            {/if}
        {/if}
    {/snippet}
</ZoomableContainer>

<style>
    .hidden {
        visibility: hidden;
        pointer-events: none;
    }
</style>
