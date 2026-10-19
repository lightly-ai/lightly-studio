<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { getAssistedLabelingTools } from '$lib/hooks/useAssistedLabelingProvider/getAssistedLabelingTools';
    import type { AssistedLabelingToolState } from '../SampleDetailsImageContainer/useAssistedLabelingTools.svelte';
    import SmartSelectOverlay from '../SmartSelectOverlay/SmartSelectOverlay.svelte';
    import InstancesOverlay from '../InstancesOverlay/InstancesOverlay.svelte';

    interface Props {
        activeTool: 'wand' | 'instances';
        collectionId: string;
        sampleId: string;
        sample: { width: number; height: number; annotations: AnnotationView[] };
        interactionRect?: SVGRectElement | null;
        refetch: () => void;
        toolState: AssistedLabelingToolState;
        tools: ReturnType<typeof getAssistedLabelingTools>;
        defaultAnnotationClass: string | null | undefined;
        annotationSource: string | null | undefined;
    }

    let {
        activeTool,
        collectionId,
        sampleId,
        sample,
        interactionRect = $bindable(),
        refetch,
        toolState,
        tools,
        defaultAnnotationClass,
        annotationSource
    }: Props = $props();

    const { lastAnnotationOutputType } = useGlobalStorage();
</script>

<!-- Keyed by sample, so points and previews of the previous sample are dropped. -->
{#key sampleId}
    {#if activeTool === 'wand'}
        <SmartSelectOverlay
            bind:interactionRect
            {collectionId}
            {sampleId}
            {sample}
            {refetch}
            outputType={$lastAnnotationOutputType}
            annotationClass={toolState.smartSelectClass ?? defaultAnnotationClass}
            {annotationSource}
            positivePoints={tools.positivePoints}
            negativePoints={tools.negativePoints}
            boxes={tools.boxes}
            onActionsChange={(actions) => (toolState.smartSelect = actions)}
        />
    {:else}
        <InstancesOverlay
            bind:interactionRect
            {collectionId}
            {sampleId}
            {sample}
            {refetch}
            prompt={toolState.instancesPrompt}
            onPromptChange={(value) => (toolState.instancesPrompt = value)}
            maxInstances={Math.min(
                toolState.maxInstances ?? tools.defaultMaxInstances,
                tools.maxInstances
            )}
            annotationClass={toolState.instancesClass ?? defaultAnnotationClass}
            {annotationSource}
            outputType={$lastAnnotationOutputType}
            isDrawingBox={toolState.isDrawingInstancesBox}
            onBoxDrawn={() => (toolState.isDrawingInstancesBox = false)}
            onStateChange={(state) => (toolState.instances = state)}
        />
    {/if}
{/key}
