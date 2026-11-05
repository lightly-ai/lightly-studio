import { SampleType } from '$lib/api/lightly_studio_local';
import { readCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

/**
 * The collection that owns the annotation sources of the collection on screen. Annotation
 * sources are child collections of the owner, so on the annotations grid, where the collection
 * on screen is a source, the owner is its parent. Undefined while the collection loads.
 */
export const useAnnotationSourceOwnerId = (
    getCollectionId: () => string
): { readonly ownerCollectionId: string | undefined } => {
    const collection = createQuery(() => ({
        ...readCollectionOptions({ path: { collection_id: getCollectionId() } }),
        enabled: !!getCollectionId()
    }));

    return {
        get ownerCollectionId() {
            const data = collection.data;
            if (!data) return undefined;
            if (data.sample_type !== SampleType.ANNOTATION) return data.collection_id;
            return data.parent_collection_id ?? undefined;
        }
    };
};
