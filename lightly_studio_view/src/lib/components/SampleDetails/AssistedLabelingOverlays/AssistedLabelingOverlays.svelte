<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import SmartSelectOverlay from '$lib/components/SampleDetails/SmartSelectOverlay/SmartSelectOverlay.svelte';
    import FindInstancesOverlay from '$lib/components/SampleDetails/FindInstancesOverlay/FindInstancesOverlay.svelte';
    import type { useAssistedLabelingTools } from '$lib/hooks/useAssistedLabelingTools';

    interface Props {
        sample: { sampleId: string; width: number; height: number };
        visibleAnnotations: AnnotationView[];
        scale: number;
        interactionRect?: SVGRectElement | null;
        assistedLabeling: ReturnType<typeof useAssistedLabelingTools>;
    }

    let {
        sample,
        visibleAnnotations,
        scale,
        interactionRect = $bindable(),
        assistedLabeling
    }: Props = $props();
</script>

<!-- Keyed by sample, so a box drag on the previous sample is dropped. -->
{#key sample.sampleId}
    {#if assistedLabeling.activeTool === 'smart-select'}
        <SmartSelectOverlay
            bind:interactionRect
            {sample}
            annotations={visibleAnnotations}
            {scale}
            isPanning={assistedLabeling.isPanning}
            saveAs={assistedLabeling.state.saveAs}
            smartSelect={assistedLabeling.smartSelect}
        />
    {:else if assistedLabeling.activeTool === 'find-instances'}
        <FindInstancesOverlay
            bind:interactionRect
            {sample}
            {scale}
            saveAs={assistedLabeling.state.saveAs}
            isDrawingBox={assistedLabeling.state.isDrawingInstancesBox}
            onBoxDrawn={() => (assistedLabeling.state.isDrawingInstancesBox = false)}
            instances={assistedLabeling.instances}
        />
    {/if}
{/key}
