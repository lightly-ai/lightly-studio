<script lang="ts">
    import { AnnotationType } from '$lib/api/lightly_studio_local';
    import VectorSquareIcon from '$lib/components/VectorSquareIcon/VectorSquareIcon.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';

    const annotationLabelContext = useAnnotationLabelContext();
    let sampleDetailsToolbarContext = useSampleDetailsToolbarContext();

    const isFocused = $derived.by(() => sampleDetailsToolbarContext.status === 'bounding-box');
</script>

<button
    type="button"
    onclick={() => {
        if (sampleDetailsToolbarContext.status === 'bounding-box') {
            sampleDetailsToolbarContext.status = 'none';

            annotationLabelContext.annotationType = null;
            annotationLabelContext.annotationLabel = null;
            annotationLabelContext.lastCreatedAnnotationId = null;
            return;
        } else {
            sampleDetailsToolbarContext.status = 'bounding-box';
            annotationLabelContext.annotationType = AnnotationType.OBJECT_DETECTION;
        }
    }}
    aria-label="Bounding Box Tool"
    class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none
                ${isFocused ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <VectorSquareIcon
        className={`size-6 transition-colors ${isFocused ? 'text-primary' : ''} hover:text-primary`}
    />
</button>
