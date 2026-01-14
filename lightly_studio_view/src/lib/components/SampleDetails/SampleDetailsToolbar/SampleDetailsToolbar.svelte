<script lang="ts">
    import SampleDetailsToolbarTooltip from '$lib/components/SampleDetails/SampleDetailsToolbarTooltip/SampleDetailsToolbarTooltip.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { onMount } from 'svelte';
    import BoundingBoxToolbarButton from '../BoundingBoxToolbarButton/BoundingBoxToolbarButton.svelte';
    import BrushToolbarButton from '../BrushToolbarButton/BrushToolbarButton.svelte';
    import CursorToolbarButton from '../CursorToolbarButton/CursorToolbarButton.svelte';

    const {
        setAnnotationId,
        setAnnotationLabel,
        setAnnotationType,
        setLastCreatedAnnotationId,
        setIsDrawing,
        setIsErasing
    } = useAnnotationLabelContext();

    const { context: sampleDetailsToolbarContext, setBrushMode } = useSampleDetailsToolbarContext();
    let { setStatus } = useSampleDetailsToolbarContext();

    onMount(() => {
        setStatus('cursor');
    });

    $effect(() => {
        // Reset annotation label and type when switching to cursor tool
        if (sampleDetailsToolbarContext.status === 'cursor') {
            setAnnotationLabel(null);
            setAnnotationId(null);
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
    });
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
        <SampleDetailsToolbarTooltip label="Cursor Tool">
            <CursorToolbarButton />
        </SampleDetailsToolbarTooltip>
        <SampleDetailsToolbarTooltip label="Bounding Box Tool">
            <BoundingBoxToolbarButton />
        </SampleDetailsToolbarTooltip>
        <SampleDetailsToolbarTooltip label="Brush Tool">
            <BrushToolbarButton />
        </SampleDetailsToolbarTooltip>
    </div>
</div>
