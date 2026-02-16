<script lang="ts">
    import SteppingNavigation from './SteppingNavigation.svelte';
    import { createAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';

    const {
        hasPrevious,
        hasNext,
        onNext,
        onPrevious
    }: {
        hasPrevious: boolean;
        hasNext: boolean;
        onNext: () => void;
        onPrevious: () => void;
    } = $props();

    // Provide the annotation label context required by SteppingNavigation.
    createAnnotationLabelContext({ isDrawing: false });
</script>

<SteppingNavigation {hasPrevious} {hasNext} {onNext} {onPrevious} />
