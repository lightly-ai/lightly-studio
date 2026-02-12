<script lang="ts">
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import SteppingNavigation from '../SteppingNavigation/SteppingNavigation.svelte';

    type Props = {
        hasPrevious: boolean;
        hasNext: boolean;
        onNext: () => void;
        onPrevious: () => void;
    };

    const { hasPrevious, hasNext, onNext, onPrevious }: Props = $props();

    const { context } = useAnnotationLabelContext();
</script>

<SteppingNavigation {hasPrevious} {hasNext} {onPrevious} {onNext} isDrawing={context.isDrawing} />
