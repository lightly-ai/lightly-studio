<script lang="ts">
    import { AnnotationType } from '$lib/api/lightly_studio_local';
    import SampleDetailsToolbarTooltip from '$lib/components/SampleDetails/SampleDetailsToolbarTooltip/SampleDetailsToolbarTooltip.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { onDestroy, onMount } from 'svelte';
    import BoundingBoxToolbarButton from '../BoundingBoxToolbarButton/BoundingBoxToolbarButton.svelte';
    import BrushToolbarButton from '../BrushToolbarButton/BrushToolbarButton.svelte';
    import CursorToolbarButton from '../CursorToolbarButton/CursorToolbarButton.svelte';

    const onKeyDown = (e: KeyboardEvent) => {
        const target = e.target as HTMLElement;
        if (
            target.tagName === 'INPUT' ||
            target.tagName === 'TEXTAREA' ||
            target.isContentEditable
        ) {
            return;
        }

        const key = e.key.toLowerCase();
        if (key === 'c') {
            e.preventDefault();
            onClickCursor();
        } else if (key === 'b') {
            e.preventDefault();
            onClickBoundingBox();
        } else if (key === 'u') {
            e.preventDefault();
            onClickBrush();
        }
    };

    onMount(() => {
        window.addEventListener('keydown', onKeyDown);
    });

    onDestroy(() => {
        window.removeEventListener('keydown', onKeyDown);
    });

    const annotationLabelContext = useAnnotationLabelContext();
    const sampleDetailsToolbarContext = useSampleDetailsToolbarContext();

    $effect(() => {
        // Reset annotation label and type when switching to cursor tool
        if (sampleDetailsToolbarContext.status === 'cursor') {
            annotationLabelContext.annotationLabel = null;
            annotationLabelContext.lastCreatedAnnotationId = null;
            annotationLabelContext.annotationType = null;
            annotationLabelContext.isDrawing = false;
            annotationLabelContext.isErasing = false;
            annotationLabelContext.annotationLabel = null;
            annotationLabelContext.annotationId = null;
            annotationLabelContext.lastCreatedAnnotationId = null;
            sampleDetailsToolbarContext.brush.mode = 'brush';
        } else if (
            sampleDetailsToolbarContext.status === 'bounding-box' ||
            sampleDetailsToolbarContext.status === 'brush'
        ) {
            annotationLabelContext.lastCreatedAnnotationId = null;
            sampleDetailsToolbarContext.brush.mode = 'brush';
        }
    });

    const onClickBoundingBox = () => {
        if (sampleDetailsToolbarContext.status == 'bounding-box') {
            sampleDetailsToolbarContext.status = 'cursor';
            annotationLabelContext.annotationType = null;
        } else {
            sampleDetailsToolbarContext.status = 'bounding-box';
            annotationLabelContext.annotationType = AnnotationType.OBJECT_DETECTION;
        }

        annotationLabelContext.annotationLabel = null;
        annotationLabelContext.annotationId = null;
    };

    const onClickCursor = () => {
        sampleDetailsToolbarContext.status = 'cursor';
    };

    const onClickBrush = () => {
        if (sampleDetailsToolbarContext.status === 'brush') {
            sampleDetailsToolbarContext.status = 'cursor';
            annotationLabelContext.annotationType = null;
        } else {
            sampleDetailsToolbarContext.status = 'brush';
            annotationLabelContext.annotationType = AnnotationType.INSTANCE_SEGMENTATION;
        }

        annotationLabelContext.annotationLabel = null;
        annotationLabelContext.annotationId = null;
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
        <SampleDetailsToolbarTooltip label="Cursor Tool" shortcut="C">
            <CursorToolbarButton onclick={onClickCursor} />
        </SampleDetailsToolbarTooltip>
        <SampleDetailsToolbarTooltip label="Bounding Box Tool" shortcut="B">
            <BoundingBoxToolbarButton onclick={onClickBoundingBox} />
        </SampleDetailsToolbarTooltip>
        <SampleDetailsToolbarTooltip label="Brush Tool" shortcut="U">
            <BrushToolbarButton onclick={onClickBrush} />
        </SampleDetailsToolbarTooltip>
    </div>
</div>
