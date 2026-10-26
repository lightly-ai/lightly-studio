<script lang="ts">
    import { page } from '$app/state';
    import { useBulkDeleteAnnotations } from '$lib/hooks';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { get } from 'svelte/store';
    import { toast } from 'svelte-sonner';
    import DeleteAnnotationsDialog from '../DeleteAnnotationsDialog/DeleteAnnotationsDialog.svelte';

    interface Props {
        collectionId: string;
    }

    let { collectionId }: Props = $props();

    const { user } = useAuth();
    const {
        isEditingMode,
        selectedSampleAnnotationCropIds,
        getSelectAllAnnotationSnapshot,
        clearSelectedSampleAnnotationCrops
    } = useGlobalStorage();
    const { deleteAnnotations, isPending } = useBulkDeleteAnnotations();

    const canDelete = $derived($isEditingMode && hasMinimumRole(user?.role, 'labeler'));
    const selectedIds = $derived($selectedSampleAnnotationCropIds[collectionId] ?? new Set());

    async function handleDelete() {
        if (get(isPending)) return;
        const snapshot = get(getSelectAllAnnotationSnapshot(collectionId));
        const result = await deleteAnnotations({
            collectionId,
            rootCollectionId: page.params.dataset_id!,
            selectedIds,
            selectAllSnapshot:
                snapshot?.filter.filter_type === 'annotations'
                    ? { filter: snapshot.filter, size: snapshot.size }
                    : null
        });
        if (result.ok) {
            clearSelectedSampleAnnotationCrops(collectionId);
            const noun = result.deletedCount === 1 ? 'annotation' : 'annotations';
            toast.success(`Deleted ${result.deletedCount} ${noun}`);
        } else {
            toast.error('Failed to delete annotations. Please try again.');
        }
    }
</script>

{#if canDelete}
    <DeleteAnnotationsDialog
        selectedCount={selectedIds.size}
        isDeleting={$isPending}
        onDelete={handleDelete}
    />
{/if}
