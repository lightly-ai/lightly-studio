import { renameAnnotationSource } from '$lib/api/lightly_studio_local';
import { useQueryClient } from '@tanstack/svelte-query';
import { readonly, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';

interface Source {
    id: string;
    name: string;
}

interface Params {
    /** The collection that owns the annotation sources. */
    collectionId: string;
    sources: Source[];
    onRenamed: (source: Source, newName: string) => void;
}

const FALLBACK_ERROR = 'Could not rename the annotation source. Try again.';

export const useRenameAnnotationSource = (getParams: () => Params) => {
    const client = useQueryClient();
    const renamingId = writable<string | null>(null);

    const rename = async (source: Source, newName: string) => {
        const { collectionId, sources, onRenamed } = getParams();
        if (sources.some((other) => other.id !== source.id && other.name === newName)) {
            toast.error(`An annotation source named “${newName}” already exists.`);
            return;
        }
        renamingId.set(source.id);
        try {
            const { error } = await renameAnnotationSource({
                path: { collection_id: collectionId, annotation_collection_id: source.id },
                body: { name: newName }
            });
            if (error) {
                toast.error((error as { error?: string })?.error ?? FALLBACK_ERROR);
                return;
            }
            // Source names show in filters, panels, pills and evaluations, so refetch everything.
            client.invalidateQueries();
            onRenamed(source, newName);
        } catch {
            toast.error(FALLBACK_ERROR);
        } finally {
            renamingId.set(null);
        }
    };

    return { rename, renamingId: readonly(renamingId) };
};
