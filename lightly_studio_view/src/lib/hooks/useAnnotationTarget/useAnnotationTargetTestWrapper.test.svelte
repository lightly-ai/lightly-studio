<script lang="ts">
    import { onMount } from 'svelte';
    import {
        createAnnotationLabelContext,
        type AnnotationLabelContext
    } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotationTarget } from './useAnnotationTarget.svelte';

    const { onContext }: { onContext: (context: AnnotationLabelContext) => void } = $props();

    const context = createAnnotationLabelContext();
    const target = useAnnotationTarget({
        getCollectionId: () => 'col-1',
        getIsTargetHidden: () => false
    });
    onMount(() => onContext(context));
</script>

<output data-testid="target-source">{target.targetSource ?? 'none'}</output>
