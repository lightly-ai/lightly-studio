<script lang="ts">
    import { SelectableBox } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

    let {
        sampleId,
        collectionId
    }: {
        sampleId: string;
        collectionId: string;
    } = $props();

    const { getSelectedSampleIds, toggleSampleSelection } = useGlobalStorage();

    const selectedSampleIds = getSelectedSampleIds(collectionId);
</script>

<div class="absolute right-4 top-2 z-30 flex items-center gap-2">
    <SelectableBox
        onSelect={() => toggleSampleSelection(sampleId, collectionId)}
        isSelected={$selectedSampleIds.has(sampleId)}
    />
</div>
