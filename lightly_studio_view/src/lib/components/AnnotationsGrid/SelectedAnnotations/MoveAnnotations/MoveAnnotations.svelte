<script lang="ts">
    import { AnnotationSourcePicker } from '$lib/components/AnnotationSourcePicker';
    import { useGlobalStorage, useMoveAnnotationsToSource } from '$lib/hooks';
    import { useCollection } from '$lib/hooks/useCollection/useCollection';
    import { FolderInput } from '@lucide/svelte';
    import { untrack } from 'svelte';

    interface Props {
        /** The annotation source that the grid shows. */
        collectionId: string;
        disabled?: boolean;
    }

    const { collectionId, disabled = false }: Props = $props();
    // The sources are children of the collection that owns the source on screen.
    const { collection } = useCollection({ collectionId: untrack(() => collectionId) });
    const ownerCollectionId = $derived(collection.data?.parent_collection_id ?? '');
    const { selectedSampleAnnotationCropIds, clearSelectedSampleAnnotationCrops } =
        useGlobalStorage();
    const { moveToSource, isPending } = useMoveAnnotationsToSource();
    const selectedIds = $derived([...($selectedSampleAnnotationCropIds[collectionId] ?? [])]);

    async function move(sourceName: string) {
        const moved = await moveToSource({
            collectionId: ownerCollectionId,
            annotationIds: selectedIds,
            sourceName
        });
        if (moved) clearSelectedSampleAnnotationCrops(collectionId);
        return moved;
    }
</script>

<AnnotationSourcePicker
    collectionId={ownerCollectionId}
    excludeSourceId={collectionId}
    label="Move the selected annotations to another annotation source"
    heading="Move to"
    icon={FolderInput}
    triggerText="Move to annotation source"
    disabled={disabled || $isPending || selectedIds.length === 0}
    onPick={move}
/>
