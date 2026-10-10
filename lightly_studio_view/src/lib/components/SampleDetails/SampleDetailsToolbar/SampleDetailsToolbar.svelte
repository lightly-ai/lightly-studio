<script lang="ts">
    import { AnnotationType } from '$lib/api/lightly_studio_local';
    import { SampleDetailsToolbarTooltip } from '$lib/components/SampleDetails/SampleDetailsToolbarTooltip';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { onDestroy, onMount } from 'svelte';
    import { isOverlayTarget, isTextInputTarget } from '$lib/utils';
    import BoundingBoxToolbarButton from '../BoundingBoxToolbarButton/BoundingBoxToolbarButton.svelte';
    import BrushToolbarButton from '../BrushToolbarButton/BrushToolbarButton.svelte';
    import CursorToolbarButton from '../CursorToolbarButton/CursorToolbarButton.svelte';
    import DragToolbarButton from '../DragToolbarButton/DragToolbarButton.svelte';
    import { useSettings } from '$lib/hooks/useSettings';
    import SlicToolbarButton from '../SlicToolbarButton/SlicToolbarButton.svelte';
    import AssistedLabelingToolbarButtons from '../AssistedLabelingToolbarButtons/AssistedLabelingToolbarButtons.svelte';
    import { isFrameDetailsRoute } from '$lib/routes';
    import { page } from '$app/state';

    import { getSlicEngine } from '@lightly-ai/slic';

    let slicAvailable = $state(false);
    onMount(() => {
        let active = true;
        void getSlicEngine().then(
            () => {
                if (active) slicAvailable = true;
            },
            // Unsupported or blocked WASM keeps the toolbar entry hidden.
            (error) => console.error('AI-assisted labeling initialization failed', error)
        );
        return () => {
            active = false;
        };
    });

    const {
        showSegmentationTool = true,
        isPending = false
    }: {
        showSegmentationTool?: boolean;
        isPending?: boolean;
    } = $props();

    const { settingsStore } = useSettings();
    let isSpacePressed = false;

    const onKeyDown = (e: KeyboardEvent) => {
        // Typing in a field or in an overlay must not trigger the shortcuts behind it.
        if (isTextInputTarget(e.target) || isOverlayTarget(e.target)) {
            return;
        }

        if (e.code === 'Space') {
            isSpacePressed = true;
            return;
        }

        if (isSpacePressed) {
            return;
        }

        const key = e.key.toLowerCase();
        if (key === $settingsStore.key_toolbar_selection) {
            e.preventDefault();
            onClickCursor();
        } else if (key === $settingsStore.key_toolbar_bounding_box) {
            e.preventDefault();
            activateBoundingBox();
        } else if (key === $settingsStore.key_toolbar_segmentation_mask) {
            if (!showSegmentationTool) return;
            e.preventDefault();
            activateBrush();
        } else if (key === ($settingsStore.key_toolbar_slic ?? 'a').toLowerCase()) {
            if (!showSegmentationTool || !slicAvailable) return;
            e.preventDefault();
            if (e.repeat || annotationLabelContext.isDrawing || isPending) return;
            onClickSlic();
            if (!annotationLabelContext.isOnAnnotationDetailsView) setAnnotationId(null);
        } else if (key === $settingsStore.key_toolbar_drag) {
            e.preventDefault();
            onClickDrag();
        }
    };

    const onKeyUp = (e: KeyboardEvent) => {
        if (e.code === 'Space') {
            isSpacePressed = false;
        }
    };

    const onWindowBlur = () => {
        isSpacePressed = false;
    };

    onMount(() => {
        window.addEventListener('keydown', onKeyDown);
        window.addEventListener('keyup', onKeyUp);
        window.addEventListener('blur', onWindowBlur);
    });

    onDestroy(() => {
        window.removeEventListener('keydown', onKeyDown);
        window.removeEventListener('keyup', onKeyUp);
        window.removeEventListener('blur', onWindowBlur);
    });

    const {
        context: annotationLabelContext,
        setAnnotationId,
        setAnnotationType,
        setLastCreatedAnnotationId,
        setIsDrawing,
        setIsErasing
    } = useAnnotationLabelContext();

    const {
        context: sampleDetailsToolbarContext,
        setBrushMode,
        setStatus
    } = useSampleDetailsToolbarContext();

    $effect(() => {
        // Reset annotation label and type when switching to cursor tool
        if (sampleDetailsToolbarContext.status === 'cursor') {
            if (!annotationLabelContext.isOnAnnotationDetailsView) setAnnotationId(null);
            setAnnotationType(null);
            setLastCreatedAnnotationId(null);
            setIsDrawing(false);
            setIsErasing(false);

            setBrushMode('brush');
        } else if (
            sampleDetailsToolbarContext.status === 'bounding-box' ||
            sampleDetailsToolbarContext.status === 'brush' ||
            sampleDetailsToolbarContext.status === 'slic'
        ) {
            setLastCreatedAnnotationId(null);
            if (sampleDetailsToolbarContext.status === 'bounding-box') {
                if (!annotationLabelContext.isOnAnnotationDetailsView) {
                    setAnnotationType(AnnotationType.OBJECT_DETECTION);
                }
                setBrushMode('brush');
            } else if (sampleDetailsToolbarContext.status === 'brush') {
                setAnnotationType(AnnotationType.SEGMENTATION_MASK);
            } else if (sampleDetailsToolbarContext.status === 'slic') {
                setAnnotationType(AnnotationType.SEGMENTATION_MASK);
                setBrushMode('brush');
            }
        }
        if (sampleDetailsToolbarContext.status === 'drag') {
            setAnnotationType(null);
        }
        if (
            sampleDetailsToolbarContext.status === 'wand' ||
            sampleDetailsToolbarContext.status === 'instances'
        ) {
            setLastCreatedAnnotationId(null);
            setIsDrawing(false);
            setIsErasing(false);
        }
    });

    const activateBoundingBox = () => {
        if (annotationLabelContext.isOnAnnotationDetailsView) return;

        setStatus('bounding-box');
        setAnnotationType(AnnotationType.OBJECT_DETECTION);
        setAnnotationId(null);
        setLastCreatedAnnotationId(null);
    };

    const onClickBoundingBox = () => activateBoundingBox();

    const onClickCursor = () => {
        setStatus('cursor');
    };

    const onClickDrag = () => {
        setStatus('drag');
    };

    const activateBrush = () => {
        if (!showSegmentationTool) return;

        setStatus('brush');
        setAnnotationType(AnnotationType.SEGMENTATION_MASK);
        if (!annotationLabelContext.isOnAnnotationDetailsView) setAnnotationId(null);
        setLastCreatedAnnotationId(null);
    };

    const onClickBrush = () => activateBrush();

    const onClickSlic = () => {
        if (!showSegmentationTool || !slicAvailable) return;

        const shouldKeepSelectedAnnotation =
            annotationLabelContext.annotationId != null &&
            annotationLabelContext.annotationType === AnnotationType.SEGMENTATION_MASK;

        setStatus('slic');
        setAnnotationType(AnnotationType.SEGMENTATION_MASK);
        if (!annotationLabelContext.isOnAnnotationDetailsView && !shouldKeepSelectedAnnotation) {
            setAnnotationId(null);
        }
        setLastCreatedAnnotationId(null);
    };
</script>

<div class="pointer-events-none absolute left-1 top-1 z-20">
    <div
        class="
      pointer-events-auto
      flex
      select-none
      flex-col
      items-stretch
      gap-1
      rounded-lg
      bg-muted
      p-1
      shadow-md
    "
    >
        <SampleDetailsToolbarTooltip
            label="Select"
            shortcut={$settingsStore.key_toolbar_selection.toUpperCase()}
            action="select"
        >
            <CursorToolbarButton onclick={onClickCursor} />
        </SampleDetailsToolbarTooltip>
        <SampleDetailsToolbarTooltip
            label="Drag"
            shortcut={$settingsStore.key_toolbar_drag.toUpperCase()}
            action="pan"
            hint="Hold Space to pan temporarily"
        >
            <DragToolbarButton onclick={onClickDrag} />
        </SampleDetailsToolbarTooltip>
        {#if !annotationLabelContext.isOnAnnotationDetailsView}
            <SampleDetailsToolbarTooltip
                label="Bounding Box"
                shortcut={$settingsStore.key_toolbar_bounding_box.toUpperCase()}
                action="draw"
            >
                <BoundingBoxToolbarButton onclick={onClickBoundingBox} />
            </SampleDetailsToolbarTooltip>
        {/if}
        {#if showSegmentationTool && slicAvailable}
            <SampleDetailsToolbarTooltip
                label="AI-Assisted labeling"
                shortcut={($settingsStore.key_toolbar_slic ?? 'a').toUpperCase()}
                action="activate"
            >
                <SlicToolbarButton
                    onclick={onClickSlic}
                    isActive={sampleDetailsToolbarContext.status === 'slic'}
                />
            </SampleDetailsToolbarTooltip>
        {/if}
        <!-- The AI-assisted labeling backend supports images only, not video frames. -->
        {#if !annotationLabelContext.isOnAnnotationDetailsView && !isFrameDetailsRoute(page.route.id)}
            <AssistedLabelingToolbarButtons
                status={sampleDetailsToolbarContext.status}
                onActivate={setStatus}
            />
        {/if}
        {#if showSegmentationTool}
            <SampleDetailsToolbarTooltip
                label="Segmentation Mask Brush"
                shortcut={$settingsStore.key_toolbar_segmentation_mask.toUpperCase()}
                action="paint"
            >
                <BrushToolbarButton
                    onclick={onClickBrush}
                    isActive={sampleDetailsToolbarContext.status === 'brush' &&
                        annotationLabelContext.annotationType === AnnotationType.SEGMENTATION_MASK}
                />
            </SampleDetailsToolbarTooltip>
        {/if}
    </div>
</div>
