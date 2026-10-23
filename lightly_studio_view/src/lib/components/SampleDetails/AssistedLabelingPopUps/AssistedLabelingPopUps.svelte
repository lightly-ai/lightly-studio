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
    const instances = $derived(assistedLabeling.instances);
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
        boxCount={instances.boxes.length}
        isGenerating={instances.isGenerating}
        resultCount={instances.predictions.length}
        canSave={instances.canSave}
        onGenerate={() => void instances.generate()}
        onSave={() => void instances.save()}
        onClear={() => {
            instances.clear();
            toolState.instancesPrompt = '';
        }}
    />
{/if}
