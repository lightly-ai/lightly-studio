<script lang="ts">
    import SmartSelectPopUp from '$lib/components/SampleDetails/SmartSelectPopUp/SmartSelectPopUp.svelte';
    import type { useAssistedLabelingTools } from '$lib/hooks/useAssistedLabelingTools';

    interface Props {
        collectionId: string;
        assistedLabeling: ReturnType<typeof useAssistedLabelingTools>;
    }

    let { collectionId, assistedLabeling }: Props = $props();

    const toolState = $derived(assistedLabeling.state);
</script>

{#if assistedLabeling.activeTool === 'smart-select' && !assistedLabeling.isPanning}
    <SmartSelectPopUp
        {collectionId}
        saveAs={toolState.saveAs}
        onSaveAsChange={(value) => (toolState.saveAs = value)}
        annotationClass={assistedLabeling.smartSelectClass}
        onAnnotationClassChange={(value) => (toolState.smartSelectClass = value)}
        canSave={toolState.smartSelect.canSave}
        isPending={toolState.smartSelect.isPending}
        needsPositivePoint={toolState.smartSelect.needsPositivePoint}
        onSave={toolState.smartSelect.save}
        onClear={toolState.smartSelect.clear}
    />
{/if}
