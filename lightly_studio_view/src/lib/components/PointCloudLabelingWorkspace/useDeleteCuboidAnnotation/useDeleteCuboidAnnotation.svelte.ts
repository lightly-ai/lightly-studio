import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useDeleteAnnotation } from '$lib/hooks';
import { toast } from 'svelte-sonner';

interface Params {
    getCollectionId: () => string | undefined;
    getAnnotations: () => readonly AnnotationView[];
}

export function useDeleteCuboidAnnotation({ getCollectionId, getAnnotations }: Params) {
    const { deleteAnnotation } = useDeleteAnnotation({
        getCollectionId: () => getCollectionId() ?? ''
    });
    const deletingIds = new Set<string>();

    async function handleDeleteCuboid(cuboidId: string): Promise<boolean> {
        if (deletingIds.has(cuboidId)) return false;

        const annotation = getAnnotations().find((a) => a.sample_id === cuboidId);
        if (!annotation) return false;

        deletingIds.add(cuboidId);
        try {
            await deleteAnnotation(cuboidId, annotation.annotation_type);
            toast.success('Annotation deleted successfully');
            return true;
        } catch {
            toast.error('Failed to delete annotation. Please try again.');
            return false;
        } finally {
            deletingIds.delete(cuboidId);
        }
    }

    return { handleDeleteCuboid };
}
