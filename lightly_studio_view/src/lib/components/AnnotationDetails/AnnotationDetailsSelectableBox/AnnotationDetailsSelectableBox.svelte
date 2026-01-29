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

    const { selectedSampleAnnotationCropIds, toggleSampleAnnotationCropSelection } =
        useGlobalStorage();
</script>

<div class="absolute right-4 top-2 z-30 flex items-center gap-2">
    <SelectableBox
        onSelect={() => toggleSampleAnnotationCropSelection(collectionId, sampleId)}
        isSelected={$selectedSampleAnnotationCropIds[collectionId]?.has(sampleId)}
    />
</div>
