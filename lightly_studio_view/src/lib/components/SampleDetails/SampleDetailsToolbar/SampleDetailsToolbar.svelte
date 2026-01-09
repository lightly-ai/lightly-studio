<script lang="ts">
    import SampleDetailsToolbarTooltip from '$lib/components/SampleDetails/SampleDetailsToolbarTooltip/SampleDetailsToolbarTooltip.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import BoundingBoxToolbarButton from '../BoundingBoxToolbarButton/BoundingBoxToolbarButton.svelte';
    import BrushToolbarButton from '../BrushToolbarButton/BrushToolbarButton.svelte';
    import CursorToolbarButton from '../CursorToolbarButton/CursorToolbarButton.svelte';

    const annotationLabelContext = useAnnotationLabelContext();
    const sampleDetailsToolbarContext = useSampleDetailsToolbarContext();

    $effect(() => {
        // Reset annotation label and type when switching to cursor tool
        if (sampleDetailsToolbarContext.status === 'cursor') {
            annotationLabelContext.annotationLabel = null;
            annotationLabelContext.lastCreatedAnnotationId = null;
            annotationLabelContext.annotationType = null;
        } else if (
            sampleDetailsToolbarContext.status === 'bounding-box' ||
            sampleDetailsToolbarContext.status === 'brush'
        ) {
            annotationLabelContext.annotationLabel = null;
            annotationLabelContext.lastCreatedAnnotationId = null;

            sampleDetailsToolbarContext.brush.mode = 'brush';
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
