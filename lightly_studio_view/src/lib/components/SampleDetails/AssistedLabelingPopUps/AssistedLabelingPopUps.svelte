<script lang="ts">
    import SmartSelectPopUp from '$lib/components/SampleDetails/SmartSelectPopUp/SmartSelectPopUp.svelte';
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
{/if}
