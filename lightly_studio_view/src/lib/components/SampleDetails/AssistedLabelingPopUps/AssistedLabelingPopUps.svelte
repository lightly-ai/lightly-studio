<script lang="ts">
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import SmartSelectPopUp from '$lib/components/SampleDetails/SmartSelectPopUp/SmartSelectPopUp.svelte';
    import type { useAssistedLabelingTools } from '$lib/hooks/useAssistedLabelingTools';

    interface Props {
        collectionId: string;
        assistedLabeling: ReturnType<typeof useAssistedLabelingTools>;
    }

    let { collectionId, assistedLabeling }: Props = $props();

    // The tool status outlives edit mode, so the pop-ups check it.
    const { isEditingMode } = useGlobalStorage();
    const toolState = $derived(assistedLabeling.state);
</script>

{#if $isEditingMode && assistedLabeling.activeTool === 'smart-select'}
    <SmartSelectPopUp
        {collectionId}
        saveAs={toolState.saveAs}
        onSaveAsChange={(value) => (toolState.saveAs = value)}
        annotationClass={assistedLabeling.smartSelectClass}
        onAnnotationClassChange={(value) => (toolState.smartSelectClass = value)}
        canSave={toolState.smartSelect.canSave}
        onSave={toolState.smartSelect.save}
        onClear={toolState.smartSelect.clear}
    />
{/if}
