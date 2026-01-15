<script lang="ts">
    import { AnnotationType } from '$lib/api/lightly_studio_local';
    import VectorSquareIcon from '$lib/components/VectorSquareIcon/VectorSquareIcon.svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';

    const { setAnnotationType, setAnnotationId, setAnnotationLabel } = useAnnotationLabelContext();
    let { context: sampleDetailsToolbarContext, setStatus } = useSampleDetailsToolbarContext();

    const isFocused = $derived(sampleDetailsToolbarContext.status === 'bounding-box');
</script>

<button
    type="button"
    onclick={() => {
        if (isFocused) {
            setStatus('cursor');
            setAnnotationType(null);
        } else {
            setStatus('bounding-box');
            setAnnotationType(AnnotationType.OBJECT_DETECTION);
        }

        setAnnotationLabel(null);
        setAnnotationId(null);
    }}
    aria-label="Bounding Box Tool"
    class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none
                ${isFocused ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <VectorSquareIcon
        className={`size-4 transition-colors ${isFocused ? 'text-primary' : ''} hover:text-primary`}
    />
</button>
