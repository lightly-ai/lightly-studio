<script lang="ts">
    import { AnnotationType } from '$lib/api/lightly_studio_local';
    import SampleDetailsToolbarTooltip from '$lib/components/SampleDetails/SampleDetailsToolbarTooltip/SampleDetailsToolbarTooltip.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { onDestroy, onMount } from 'svelte';
    import BoundingBoxToolbarButton from '../BoundingBoxToolbarButton/BoundingBoxToolbarButton.svelte';
    import BrushToolbarButton from '../BrushToolbarButton/BrushToolbarButton.svelte';
    import CursorToolbarButton from '../CursorToolbarButton/CursorToolbarButton.svelte';
    import DragToolbarButton from '../DragToolbarButton/DragToolbarButton.svelte';
    import { useSettings } from '$lib/hooks/useSettings';
    import SemanticBrushToolbarButton from '../SemanticBrushToolbarButton/SemanticBrushToolbarButton.svelte';

    const { showSegmentationTool = true }: { showSegmentationTool?: boolean } = $props();

    const { settingsStore } = useSettings();

    const onKeyDown = (e: KeyboardEvent) => {
        const target = e.target as HTMLElement;

        if (
            target.tagName === 'TEXTAREA' ||
            target.isContentEditable ||
            target.tagName === 'INPUT'
        ) {
            return;
        }

        const key = e.key.toLowerCase();
        if (key === $settingsStore.key_toolbar_selection) {
            e.preventDefault();
            onClickCursor();
        } else if (key === $settingsStore.key_toolbar_bounding_box) {
            e.preventDefault();
            onClickBoundingBox();
        } else if (key === $settingsStore.key_toolbar_segmentation_mask) {
            if (!showSegmentationTool) return;
            e.preventDefault();
            onClickBrush();
        } else if (key === $settingsStore.key_toolbar_drag) {
            e.preventDefault();
            onClickDrag();
        } else if (key === 'g') {
            if (!showSegmentationTool) return;
            e.preventDefault();
            onClickSemanticBrush();
        }
    };

    onMount(() => {
        window.addEventListener('keydown', onKeyDown);
    });

    onDestroy(() => {
        window.removeEventListener('keydown', onKeyDown);
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

    let lastSegmentationType: AnnotationType = AnnotationType.INSTANCE_SEGMENTATION;

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
            sampleDetailsToolbarContext.status === 'brush'
        ) {
            setLastCreatedAnnotationId(null);
            if (sampleDetailsToolbarContext.status === 'bounding-box') {
                if (!annotationLabelContext.isOnAnnotationDetailsView) {
                    setAnnotationType(AnnotationType.OBJECT_DETECTION);
                }
                setBrushMode('brush');
            } else if (sampleDetailsToolbarContext.status === 'brush') {
                const typeToSet = annotationLabelContext.annotationType ?? lastSegmentationType;
                lastSegmentationType = typeToSet;
                setAnnotationType(typeToSet);
            }
        }
        if (sampleDetailsToolbarContext.status === 'drag') {
            setAnnotationType(null);
        }
    });

    const onClickBoundingBox = () => {
        if (annotationLabelContext.isOnAnnotationDetailsView) return;

        setStatus('bounding-box');
        setAnnotationType(AnnotationType.OBJECT_DETECTION);
        setAnnotationId(null);
        setLastCreatedAnnotationId(null);
    };

    const onClickCursor = () => {
        setStatus('cursor');
    };

    const onClickDrag = () => {
        setStatus('drag');
    };

    const onClickBrush = () => {
        if (!showSegmentationTool) return;

        setStatus('brush');
        lastSegmentationType = AnnotationType.INSTANCE_SEGMENTATION;
        setAnnotationType(lastSegmentationType);
        if (!annotationLabelContext.isOnAnnotationDetailsView) setAnnotationId(null);
        setLastCreatedAnnotationId(null);
    };

    const onClickSemanticBrush = () => {
        if (!showSegmentationTool || annotationLabelContext.isOnAnnotationDetailsView) return;

        setStatus('brush');
        lastSegmentationType = AnnotationType.SEMANTIC_SEGMENTATION;
        setAnnotationType(lastSegmentationType);
        if (!annotationLabelContext.isOnAnnotationDetailsView) setAnnotationId(null);
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
        {#if showSegmentationTool}
            <SampleDetailsToolbarTooltip
                label="Instance Segmentation Brush"
                shortcut={$settingsStore.key_toolbar_segmentation_mask.toUpperCase()}
                action="paint"
            >
                <BrushToolbarButton
                    onclick={onClickBrush}
                    isActive={sampleDetailsToolbarContext.status === 'brush' &&
                        annotationLabelContext.annotationType ===
                            AnnotationType.INSTANCE_SEGMENTATION}
                />
            </SampleDetailsToolbarTooltip>
            {#if !annotationLabelContext.isOnAnnotationDetailsView}
                <SampleDetailsToolbarTooltip
                    label="Semantic Segmentation Brush"
                    shortcut="G"
                    action="paint"
                >
                    <SemanticBrushToolbarButton
                        onclick={onClickSemanticBrush}
                        isActive={sampleDetailsToolbarContext.status === 'brush' &&
                            annotationLabelContext.annotationType ===
                                AnnotationType.SEMANTIC_SEGMENTATION}
                    />
                </SampleDetailsToolbarTooltip>
            {/if}
        {/if}
    </div>
</div>
