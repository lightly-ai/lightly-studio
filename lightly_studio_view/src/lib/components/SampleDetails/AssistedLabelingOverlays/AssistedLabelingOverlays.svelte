<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import SmartSelectOverlay from '$lib/components/SampleDetails/SmartSelectOverlay/SmartSelectOverlay.svelte';
    import type { useAssistedLabelingTools } from '$lib/hooks/useAssistedLabelingTools';

    interface Props {
        collectionId: string;
        sample: { sampleId: string; width: number; height: number; annotations: AnnotationView[] };
        visibleAnnotations: AnnotationView[];
        scale: number;
        interactionRect?: SVGRectElement | null;
        refetch: () => void;
        assistedLabeling: ReturnType<typeof useAssistedLabelingTools>;
    }

    let {
        collectionId,
        sample,
        visibleAnnotations,
        scale,
        interactionRect = $bindable(),
        refetch,
        assistedLabeling
    }: Props = $props();

    const { context: annotationLabelContext } = useAnnotationLabelContext();
    const toolState = $derived(assistedLabeling.state);
</script>

<!-- Keyed by sample, so the prompts and previews of the previous sample are dropped. -->
{#key sample.sampleId}
    {#if assistedLabeling.activeTool === 'smart-select'}
        <SmartSelectOverlay
            bind:interactionRect
            {collectionId}
            sampleId={sample.sampleId}
            {sample}
            annotations={visibleAnnotations}
            {scale}
            isPanning={assistedLabeling.isPanning}
            {refetch}
            saveAs={toolState.saveAs}
            annotationClass={assistedLabeling.smartSelectClass}
            annotationSource={annotationLabelContext.annotationSource}
            onActionsChange={(actions) => (toolState.smartSelect = actions)}
        />
    {/if}
{/key}
