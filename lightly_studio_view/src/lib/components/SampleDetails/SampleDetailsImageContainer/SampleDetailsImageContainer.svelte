<script lang="ts">
    import { LoaderCircle } from '@lucide/svelte';
    import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
    import { ZoomableContainer } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { afterNavigate } from '$app/navigation';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import SampleDetailsAnnotation from '../SampleDetailsAnnotation/SampleDetailsAnnotation.svelte';
    import SampleEraserRect from '../SampleEraserRect/SampleEraserRect.svelte';
    import SampleSegmentationMaskRect from '../SampleSegmentationMaskRect/SampleSegmentationMaskRect.svelte';
    import SampleObjectDetectionRect from '../SampleObjectDetectionRect/SampleObjectDetectionRect.svelte';
    import { select } from 'd3-selection';
    import {
        countVisibleSources,
        getColorByLabel,
        resolveEffectiveColorBySource
    } from '$lib/utils';
    import { useSettings } from '$lib/hooks';
    import { throttle } from 'lodash-es';
    import BrushToolPopUp from '../BrushToolPopUp/BrushToolPopUp.svelte';
    import { AnnotationSourcePill } from '$lib/components';
    import SampleDetailsToolbar from '../SampleDetailsToolbar/SampleDetailsToolbar.svelte';
    import SmartSelectOverlay from '../SmartSelectOverlay/SmartSelectOverlay.svelte';
    import SmartSelectPopUp from '../SmartSelectPopUp/SmartSelectPopUp.svelte';
    import InstancesToolPopUp from '../InstancesToolPopUp/InstancesToolPopUp.svelte';
    import InstancesOverlay from '../InstancesOverlay/InstancesOverlay.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
    import { onDestroy, onMount } from 'svelte';
    import { usePendingState } from '../usePendingState';

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

    const { isEditingMode, imageBrightness, imageContrast, lastAnnotationOutputType } =
        useGlobalStorage();
    let smartSelectOutputType = $state<'mask' | 'box'>('mask');
    let instancesOutputType = $state<'mask' | 'box'>('mask');
    let smartSelectAnnotationClass = $state<string | null>(null);
    let instancesAnnotationClass = $state<string | null>(null);
    let isDrawingInstancesBox = $state(false);
    type SmartSelectActions = {
        canSave: boolean;
        save: () => void;
        startFresh: () => void;
    };
    let smartSelectActions = $state<SmartSelectActions>({
        canSave: false,
        save: (): void => undefined,
        startFresh: (): void => undefined
    });
    type InstancesState = {
        prompt: string;
        boxCount: number;
        canGenerate: boolean;
        isGenerating: boolean;
        resultCount: number;
        generate: () => void;
        save: () => void;
        clear: () => void;
    };
    let instancesState = $state<InstancesState>({
        prompt: '',
        boxCount: 0,
        canGenerate: false,
        isGenerating: false,
        resultCount: 0,
        generate: () => undefined,
        save: () => undefined,
        clear: () => undefined
    });
    let hasInstancesState = false;
    const updateSmartSelectActions = (actions: typeof smartSelectActions) => {
        smartSelectActions = actions;
    };
    const updateInstancesState = (value: Omit<InstancesState, 'prompt'>) => {
        if (
            hasInstancesState &&
            instancesState.boxCount === value.boxCount &&
            instancesState.canGenerate === value.canGenerate &&
            instancesState.isGenerating === value.isGenerating &&
            instancesState.resultCount === value.resultCount
        ) {
            return;
        }
        hasInstancesState = true;
        instancesState = { ...value, prompt: instancesState.prompt };
    };
    $effect(() => {
        smartSelectOutputType = $lastAnnotationOutputType;
        instancesOutputType = $lastAnnotationOutputType;
    });
    const { isHidden } = useHideAnnotations();
    const { enforceColoringByClassStore } = useSettings();

    let resetZoomTransform: (() => void) | undefined = $state();
    let mousePosition = $state<{ x: number; y: number } | null>(null);
    let isHoveringBoundingBox = $state(false);
    let interactionRect: SVGRectElement | null = $state(null);
    const { isPending, handlePendingChange } = usePendingState();

    let sampleId = $derived(sample.sampleId);
    // The local hidden set is the single source of truth for visibility on the
    // details page; the grid's annotation source filter only seeds it.
    const actualAnnotationsToShow = $derived.by(() => {
        return sample.annotations
            .filter((annotation) => !hideAnnotationsIds.has(annotation.sample_id))
            .sort((a, b) => {
                if (a.sample_id === annotationLabelContext.annotationId) return 1;
                if (b.sample_id === annotationLabelContext.annotationId) return -1;
                return 0;
            });
    });

    // Color boxes by source only while annotations from multiple sources are visible and
    // class coloring is not enforced, mirroring the side panel.
    const colorBySource = $derived(
        resolveEffectiveColorBySource({
            multipleSourcesVisible:
                countVisibleSources(sample.annotations, hideAnnotationsIds) >= 2,
            enforceColoringByClass: $enforceColoringByClassStore
        })
    );

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

    const trackMousePositionOrig = (event: MouseEvent | PointerEvent) => {
        if (!interactionRect) return;

        const svgRect = interactionRect.getBoundingClientRect();
        const clientX = event.clientX;
        const clientY = event.clientY;
        const x = ((clientX - svgRect.left) / svgRect.width) * sample.width;
        const y = ((clientY - svgRect.top) / svgRect.height) * sample.height;

        mousePosition = { x, y };
    };

    const trackMousePosition = throttle(trackMousePositionOrig, 50);

    const handleGlobalPointerMove = (event: PointerEvent) => {
        trackMousePosition(event);
    };

    afterNavigate(() => {
        // Reset zoom transform when navigating to new sample
        resetZoomTransform?.();
    });

    onDestroy(() => {
        window.removeEventListener('pointermove', handleGlobalPointerMove);
    });

    onMount(() => {
        window.addEventListener('pointermove', handleGlobalPointerMove, { passive: true });
    });

    function determineHighlightForAnnotation(annotationId: string) {
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
    const annotationTypeInCurrentView = $derived(
        annotationLabelContext.isOnAnnotationDetailsView
            ? sample.annotations[0]?.annotation_type
            : annotationType
    );

    const annotationDetailsBoundingBox = $derived(
        annotationLabelContext.isOnAnnotationDetailsView && sample.annotations.length > 0
            ? getBoundingBox(sample.annotations[0])
            : undefined
    );
    const annotationDetailsFocusKey = $derived(
        annotationLabelContext.isOnAnnotationDetailsView
            ? (annotationLabelContext.annotationId ?? sample.annotations[0]?.sample_id)
            : undefined
    );
    const isSegmentationType = (type: string | null | undefined) =>
        type === AnnotationType.SEGMENTATION_MASK;

    const shouldShowBrushToolPopup = $derived.by(() => {
        if (!$isEditingMode) return false;

        if (annotationLabelContext.isOnAnnotationDetailsView) {
            return (
                isSegmentationType(sample.annotations[0]?.annotation_type) &&
                sampleDetailsToolbarContext.status === 'brush'
            );
        }

        return (
            isSegmentationType(annotationTypeInCurrentView) &&
            sampleDetailsToolbarContext.status === 'brush'
        );
    });
    const shouldShowSegmentationToolInToolbar = $derived.by(() => {
        if (annotationLabelContext.isOnAnnotationDetailsView) {
            return isSegmentationType(sample.annotations[0]?.annotation_type);
        }

        return true;
    });
</script>

<ZoomableContainer
    width={sample.width}
    height={sample.height}
    panEnabled={sampleDetailsToolbarContext.status !== 'wand' &&
        (sampleDetailsToolbarContext.status !== 'instances' || !isDrawingInstancesBox) &&
        !(annotationLabelContext.isDrawing || annotationLabelContext.isErasing)}
    cursor={'grab'}
    boundingBox={annotationDetailsBoundingBox}
    autoFocusEnabled={annotationLabelContext.isOnAnnotationDetailsView}
    autoFocusKey={annotationDetailsFocusKey}
    zoomEnabled={!annotationLabelContext.isChangingBrushSize}
    registerResetFn={(fn) => (resetZoomTransform = fn)}
>
    {#snippet toolbarContent()}
        {#if $isEditingMode}
            <SampleDetailsToolbar showSegmentationTool={shouldShowSegmentationToolInToolbar} />
        {/if}
    {/snippet}
    {#snippet zoomPanelContent()}
        {#if $isEditingMode && sampleDetailsToolbarContext.status !== 'wand' && sampleDetailsToolbarContext.status !== 'instances'}
            <div class="mb-1">
                <AnnotationSourcePill {collectionId} />
            </div>
        {/if}
        {#if shouldShowBrushToolPopup}
            <BrushToolPopUp />
        {/if}
        {#if sampleDetailsToolbarContext.status === 'wand'}
            <SmartSelectPopUp
                {collectionId}
                outputType={smartSelectOutputType}
                annotationClass={smartSelectAnnotationClass ??
                    annotationLabelContext.annotationLabel}
                onAnnotationClassChange={(value) => (smartSelectAnnotationClass = value)}
                onOutputTypeChange={(value) => (smartSelectOutputType = value)}
                canSave={smartSelectActions.canSave}
                onSave={smartSelectActions.save}
                onStartFresh={smartSelectActions.startFresh}
            />
        {/if}
        {#if sampleDetailsToolbarContext.status === 'instances'}
            <InstancesToolPopUp
                {...instancesState}
                {collectionId}
                annotationClass={instancesAnnotationClass ?? annotationLabelContext.annotationLabel}
                onAnnotationClassChange={(value) => (instancesAnnotationClass = value)}
                outputType={instancesOutputType}
                onOutputTypeChange={(value) => (instancesOutputType = value)}
                isDrawingBox={isDrawingInstancesBox}
                onDrawBox={() => (isDrawingInstancesBox = true)}
                onCancelDrawBox={() => (isDrawingInstancesBox = false)}
                canGenerate={Boolean(instancesState.prompt.trim() || instancesState.boxCount)}
                onPromptChange={(value) => (instancesState.prompt = value)}
                onGenerate={instancesState.generate}
                onSave={instancesState.save}
                onClear={instancesState.clear}
            />
        {/if}
    {/snippet}
    {#snippet zoomPanelRightContent()}
        {#if $isPending}
            <div
                class="pointer-events-auto inline-flex h-9 items-center justify-center gap-1.5 rounded-lg bg-muted/80 px-2.5 text-sm text-muted-foreground shadow-md backdrop-blur-sm"
                data-testid="finish-brush-loading-indicator"
            >
                <LoaderCircle class="size-4 animate-spin" />
                <span>Saving</span>
            </div>
        {/if}
    {/snippet}
    {#snippet zoomableContent({ scale })}
        <foreignObject x="0" y="0" width={sample.width} height={sample.height}>
            <img
                src={imageUrl}
                alt=""
                draggable="false"
                style={`height: 100%; width: 100%; filter: brightness(${$imageBrightness}) contrast(${$imageContrast})`}
            />
        </foreignObject>

        <g class:invisible={$isHidden}>
            {#each actualAnnotationsToShow as annotation (annotation.sample_id)}
                <!-- The SampleSegmentationMaskRect or SampleEraserRect component will render the preview while drawing a segmentation mask-->
                <g
                    class:hidden={annotationLabelContext.isDrawing &&
                        annotation.sample_id === annotationLabelContext.annotationId}
                >
                    <SampleDetailsAnnotation
                        annotationId={annotation.sample_id}
                        {sampleId}
                        {collectionId}
                        {isResizable}
                        onAnnotationUpdated={refetch}
                        {toggleAnnotationSelection}
                        {sample}
                        {scale}
                        {colorBySource}
                        highlight={annotationLabelContext.isDrawing
                            ? 'disabled'
                            : determineHighlightForAnnotation(annotation.sample_id)}
                    />
                </g>
            {/each}
            {#if mousePosition && $isEditingMode && (sampleDetailsToolbarContext.status === 'brush' || sampleDetailsToolbarContext.status === 'bounding-box') && !annotationLabelContext.isDrawing && !isHoveringBoundingBox}
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
                    vector-effect="non-scaling-stroke"
                    stroke-dasharray="5,5"
                    opacity="0.6"
                />
            {/if}
        </g>
        {#if $isEditingMode}
            {#if sampleDetailsToolbarContext.status === 'brush' && isSegmentationType(annotationTypeInCurrentView) && isEraser}
                <SampleEraserRect
                    bind:interactionRect
                    {collectionId}
                    {brushRadius}
                    {refetch}
                    {sample}
                    {mousePosition}
                    {drawerStrokeColor}
                    onFinishErasePendingChange={handlePendingChange}
                />
            {:else if sampleDetailsToolbarContext.status === 'brush' && isSegmentationType(annotationTypeInCurrentView)}
                <SampleSegmentationMaskRect
                    bind:interactionRect
                    {mousePosition}
                    {sampleId}
                    {collectionId}
                    {brushRadius}
                    {refetch}
                    {drawerStrokeColor}
                    {sample}
                    annotationType={annotationTypeInCurrentView}
                    onFinishBrushPendingChange={handlePendingChange}
                />
            {:else if sampleDetailsToolbarContext.status === 'bounding-box' && !annotationLabelContext.isOnAnnotationDetailsView && annotationTypeInCurrentView == AnnotationType.OBJECT_DETECTION}
                <SampleObjectDetectionRect
                    bind:interactionRect
                    bind:hoverbbox={isHoveringBoundingBox}
                    {sample}
                    {sampleId}
                    {collectionId}
                    {drawerStrokeColor}
                    {refetch}
                    onCreateBoundingBoxPendingChange={handlePendingChange}
                />
            {:else if sampleDetailsToolbarContext.status === 'wand'}
                <SmartSelectOverlay
                    {collectionId}
                    {sampleId}
                    {sample}
                    {refetch}
                    annotationClass={smartSelectAnnotationClass ??
                        annotationLabelContext.annotationLabel}
                    annotationLabel={annotationLabelContext.annotationLabel}
                    annotationSource={annotationLabelContext.annotationSource}
                    outputType={smartSelectOutputType}
                    onActionsChange={updateSmartSelectActions}
                />
            {:else if sampleDetailsToolbarContext.status === 'instances'}
                <InstancesOverlay
                    {collectionId}
                    {sampleId}
                    {sample}
                    {refetch}
                    prompt={instancesState.prompt}
                    onPromptChange={(value: string) => (instancesState.prompt = value)}
                    annotationClass={instancesAnnotationClass ??
                        annotationLabelContext.annotationLabel}
                    isDrawingBox={isDrawingInstancesBox}
                    onBoxDrawn={() => (isDrawingInstancesBox = false)}
                    annotationLabel={annotationLabelContext.annotationLabel}
                    annotationSource={annotationLabelContext.annotationSource}
                    outputType={instancesOutputType}
                    onStateChange={updateInstancesState}
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
