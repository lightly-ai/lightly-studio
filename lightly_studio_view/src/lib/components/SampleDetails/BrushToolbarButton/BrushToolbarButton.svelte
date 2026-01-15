<script lang="ts">
    import { AnnotationType } from '$lib/api/lightly_studio_local';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { Brush } from '@lucide/svelte';

    const { setAnnotationId, setAnnotationType, setAnnotationLabel } = useAnnotationLabelContext();
    let { context: sampleDetailsToolbarContext, setStatus } = useSampleDetailsToolbarContext();

    const isFocused = $derived(sampleDetailsToolbarContext.status === 'brush');
</script>

<button
    type="button"
    onclick={() => {
        if (isFocused) {
            setStatus('cursor');
            setAnnotationType(null);
        } else {
            setStatus('brush');
            setAnnotationType(AnnotationType.INSTANCE_SEGMENTATION);
        }

        setAnnotationId(null);
    }}
    aria-label="Brush Tool"
    class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none
                ${isFocused ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <Brush
        class={`size-4 transition-colors ${isFocused ? 'text-primary' : ''} hover:text-primary`}
    />
</button>
