<script lang="ts">
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { AssistedLabelingToolState } from '../SampleDetailsImageContainer/useAssistedLabelingTools.svelte';
    import type { getAssistedLabelingTools } from '$lib/hooks/useAssistedLabelingProvider/getAssistedLabelingTools';
    import SmartSelectPopUp from '../SmartSelectPopUp/SmartSelectPopUp.svelte';
    import InstancesToolPopUp from '../InstancesToolPopUp/InstancesToolPopUp.svelte';

    interface Props {
        activeTool: 'wand' | 'instances';
        collectionId: string;
        toolState: AssistedLabelingToolState;
        tools: ReturnType<typeof getAssistedLabelingTools>;
        defaultAnnotationClass: string | null | undefined;
    }

    let { activeTool, collectionId, toolState, tools, defaultAnnotationClass }: Props = $props();

    const { lastAnnotationOutputType, setLastAnnotationOutputType } = useGlobalStorage();
</script>

{#if activeTool === 'wand'}
    <SmartSelectPopUp
        {collectionId}
        outputType={$lastAnnotationOutputType}
        onOutputTypeChange={setLastAnnotationOutputType}
        annotationClass={toolState.smartSelectClass ?? defaultAnnotationClass}
        onAnnotationClassChange={(value) => (toolState.smartSelectClass = value)}
        positivePoints={tools.positivePoints}
        negativePoints={tools.negativePoints}
        boxes={tools.boxes}
        canSave={toolState.smartSelect.canSave}
        onSave={toolState.smartSelect.save}
        onClear={toolState.smartSelect.clear}
    />
{:else}
    <InstancesToolPopUp
        {collectionId}
        prompt={toolState.instancesPrompt}
        onPromptChange={(value) => (toolState.instancesPrompt = value)}
        maxInstances={Math.min(
            toolState.maxInstances ?? tools.defaultMaxInstances,
            tools.maxInstances
        )}
        maxInstancesLimit={tools.maxInstances}
        onMaxInstancesChange={(value) => (toolState.maxInstances = value)}
        annotationClass={toolState.instancesClass ?? defaultAnnotationClass}
        onAnnotationClassChange={(value) => (toolState.instancesClass = value)}
        outputType={$lastAnnotationOutputType}
        onOutputTypeChange={setLastAnnotationOutputType}
        canDrawBoxes={tools.boxes}
        isDrawingBox={toolState.isDrawingInstancesBox}
        onDrawBoxChange={(value) => (toolState.isDrawingInstancesBox = value)}
        boxCount={toolState.instances.boxCount}
        isGenerating={toolState.instances.isGenerating}
        resultCount={toolState.instances.resultCount}
        onGenerate={toolState.instances.generate}
        onSave={toolState.instances.save}
        onClear={toolState.instances.clear}
    />
{/if}
