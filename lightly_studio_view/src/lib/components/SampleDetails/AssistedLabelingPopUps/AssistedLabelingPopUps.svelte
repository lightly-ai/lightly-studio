<script lang="ts">
    import SmartSelectPopUp from '$lib/components/SampleDetails/SmartSelectPopUp/SmartSelectPopUp.svelte';
    import FindInstancesPopUp from '$lib/components/SampleDetails/FindInstancesPopUp/FindInstancesPopUp.svelte';
    import type { useAssistedLabelingTools } from '$lib/hooks/useAssistedLabelingTools';

    interface Props {
        collectionId: string;
        assistedLabeling: ReturnType<typeof useAssistedLabelingTools>;
    }

    let { collectionId, assistedLabeling }: Props = $props();

    const toolState = $derived(assistedLabeling.state);
    const smartSelect = $derived(assistedLabeling.smartSelect);
</script>

{#if assistedLabeling.activeTool === 'smart-select' && !assistedLabeling.isPanning}
    <SmartSelectPopUp
        {collectionId}
        saveAs={toolState.saveAs}
        onSaveAsChange={(value) => (toolState.saveAs = value)}
        annotationClass={assistedLabeling.smartSelectClass}
        onAnnotationClassChange={(value) => (toolState.smartSelectClass = value)}
        canSave={smartSelect.canSave}
        isPending={smartSelect.isPending}
        needsPositivePoint={smartSelect.needsPositivePoint}
        onSave={() => void smartSelect.save()}
        onClear={smartSelect.clear}
    />
{:else if assistedLabeling.activeTool === 'find-instances'}
    <FindInstancesPopUp
        {collectionId}
        prompt={toolState.instancesPrompt}
        onPromptChange={(value) => (toolState.instancesPrompt = value)}
        maxInstances={toolState.maxInstances}
        onMaxInstancesChange={(value) => (toolState.maxInstances = value)}
        annotationClass={assistedLabeling.instancesClass}
        onAnnotationClassChange={(value) => (toolState.instancesClass = value)}
        saveAs={toolState.saveAs}
        onSaveAsChange={(value) => (toolState.saveAs = value)}
        isDrawingBox={toolState.isDrawingInstancesBox}
        onDrawBoxChange={(value) => (toolState.isDrawingInstancesBox = value)}
        boxCount={toolState.instances.boxCount}
        isGenerating={toolState.instances.isGenerating}
        resultCount={toolState.instances.resultCount}
        canSave={toolState.instances.canSave}
        onGenerate={toolState.instances.generate}
        onSave={toolState.instances.save}
        onClear={toolState.instances.clear}
    />
{/if}
