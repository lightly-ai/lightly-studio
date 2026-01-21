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
        if (key === 's') {
            e.preventDefault();
            onClickCursor();
        } else if (key === 'b') {
            e.preventDefault();
            onClickBoundingBox();
        } else if (key === 'm') {
            e.preventDefault();
            onClickBrush();
        } else if (key === 'd') {
            e.preventDefault();
            onClickDrag();
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

    onMount(() => {
        setStatus('cursor');
    });

    $effect(() => {
        // Reset annotation label and type when switching to cursor tool
        if (sampleDetailsToolbarContext.status === 'cursor') {
            if (!annotationLabelContext.isAnnotationDetails) setAnnotationId(null);
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
            setBrushMode('brush');
        }
        if (sampleDetailsToolbarContext.status === 'drag') {
            setAnnotationType(null);
        }
    });

    const onClickBoundingBox = () => {
        if (annotationLabelContext.isAnnotationDetails) return;

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
        setStatus('brush');
        setAnnotationType(AnnotationType.INSTANCE_SEGMENTATION);
        if (!annotationLabelContext.isAnnotationDetails) setAnnotationId(null);
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
        <SampleDetailsToolbarTooltip label="Select" shortcut="S">
            <CursorToolbarButton onclick={onClickCursor} />
        </SampleDetailsToolbarTooltip>
        <SampleDetailsToolbarTooltip label="Drag" shortcut="D">
            <DragToolbarButton onclick={onClickDrag} />
        </SampleDetailsToolbarTooltip>
        {#if !annotationLabelContext.isAnnotationDetails}
            <SampleDetailsToolbarTooltip label="Bounding Box" shortcut="B">
                <BoundingBoxToolbarButton onclick={onClickBoundingBox} />
            </SampleDetailsToolbarTooltip>
        {/if}
        <SampleDetailsToolbarTooltip label="Segmentation Mask Brush" shortcut="M">
            <BrushToolbarButton onclick={onClickBrush} />
        </SampleDetailsToolbarTooltip>
    </div>
</div>
