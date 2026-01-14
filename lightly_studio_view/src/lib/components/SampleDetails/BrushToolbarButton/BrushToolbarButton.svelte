<script lang="ts">
    import { AnnotationType } from '$lib/api/lightly_studio_local';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { Brush } from '@lucide/svelte';

    const annotationLabelContext = useAnnotationLabelContext();
    let sampleDetailsToolbarContext = useSampleDetailsToolbarContext();

    const isFocused = $derived(sampleDetailsToolbarContext.status === 'brush');
</script>

<button
    type="button"
    onclick={() => {
        if (isFocused) {
            sampleDetailsToolbarContext.status = 'cursor';
            annotationLabelContext.annotationType = null;
        } else {
            sampleDetailsToolbarContext.status = 'brush';
            annotationLabelContext.annotationType = AnnotationType.INSTANCE_SEGMENTATION;
        }
    }}
    aria-label="Brush Tool"
    class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none
                ${isFocused ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <Brush
        class={`size-6 transition-colors ${isFocused ? 'text-primary' : ''} hover:text-primary`}
    />
</button>
