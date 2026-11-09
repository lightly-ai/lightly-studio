<script lang="ts">
    import SmartSelectOverlay from '$lib/components/SampleDetails/SmartSelectOverlay/SmartSelectOverlay.svelte';
    import FindInstancesOverlay from '$lib/components/SampleDetails/FindInstancesOverlay/FindInstancesOverlay.svelte';
    import type { useAssistedLabelingTools } from '$lib/hooks/useAssistedLabelingTools';

    interface Props {
        sample: { sampleId: string; width: number; height: number };
        scale: number;
        interactionRect?: SVGRectElement | null;
        assistedLabeling: ReturnType<typeof useAssistedLabelingTools>;
    }

    let { sample, scale, interactionRect = $bindable(), assistedLabeling }: Props = $props();
</script>

<!-- Keyed by sample, so a box drag on the previous sample is dropped. -->
{#key sample.sampleId}
    {#if assistedLabeling.activeTool === 'smart-select'}
        <SmartSelectOverlay
            bind:interactionRect
            {sample}
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
            isPanning={assistedLabeling.isPanning}
            saveAs={assistedLabeling.state.saveAs}
            isDrawingBox={assistedLabeling.state.isDrawingInstancesBox}
            onDrawEnd={assistedLabeling.endInstancesBoxDrawing}
            instances={assistedLabeling.instances}
        />
    {/if}
{/key}
