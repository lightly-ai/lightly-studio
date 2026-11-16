<script lang="ts">
    import { untrack, type ComponentProps } from 'svelte';
    import {
        createAnnotationLabelContext,
        type AnnotationLabelContext
    } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotationTarget } from '$lib/hooks/useAnnotationTarget/useAnnotationTarget.svelte';
    import SampleDetailsAnnotationSegment from './SampleDetailsAnnotationSegment.svelte';

    // Renders the segment with a real, reactive annotation label context and the target that
    // SampleDetailsPanel resolves, like the page does.
    type Props = ComponentProps<typeof SampleDetailsAnnotationSegment> & {
        initialContext?: AnnotationLabelContext;
        onContext?: (context: AnnotationLabelContext) => void;
    };

    const {
        initialContext = {},
        onContext,
        annotationsIdsToHide,
        collectionId,
        sampleId,
        annotations,
        isPanModeEnabled,
        refetch
    }: Props = $props();

    const context = createAnnotationLabelContext(untrack(() => initialContext));
    untrack(() => onContext?.(context));
    let hiddenIds = $state(untrack(() => annotationsIdsToHide));
    useAnnotationTarget({
        getCollectionId: () => collectionId,
        getAnnotations: () => annotations,
        getHiddenIds: () => hiddenIds
    });
</script>

<SampleDetailsAnnotationSegment
    bind:annotationsIdsToHide={hiddenIds}
    {collectionId}
    {sampleId}
    {annotations}
    {isPanModeEnabled}
    {refetch}
/>
