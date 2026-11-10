import { SampleType } from '$lib/api/lightly_studio_local';
import {
    readCollectionHierarchyOptions,
    readCollectionOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

/**
 * The collection that owns the annotation sources of the collection on screen. Annotation
 * sources are child collections of the owner, so on the annotations grid, where the collection
 * on screen is a source, the owner is its parent. On the point-cloud grid the collection on
 * screen is an MCAP SEQUENCE, and its GROUP child owns the sources. Undefined while the
 * collections load or when they fail to load.
 */
export const useAnnotationSourceOwnerId = (
    getCollectionId: () => string
): { readonly ownerCollectionId: string | undefined; readonly isError: boolean } => {
    const collection = createQuery(() => ({
        ...readCollectionOptions({ path: { collection_id: getCollectionId() } }),
        enabled: !!getCollectionId()
    }));
    const hierarchy = createQuery(() => ({
        ...readCollectionHierarchyOptions({ path: { collection_id: getCollectionId() } }),
        enabled: collection.data?.sample_type === SampleType.SEQUENCE
    }));

    return {
        get ownerCollectionId() {
            const data = collection.data;
            if (!data) return undefined;
            if (data.sample_type === SampleType.ANNOTATION) {
                return data.parent_collection_id ?? undefined;
            }
            if (data.sample_type !== SampleType.SEQUENCE) return data.collection_id;
            if (!hierarchy.data) return undefined;
            const group = hierarchy.data.find(
                (candidate) =>
                    candidate.sample_type === SampleType.GROUP &&
                    candidate.parent_collection_id === data.collection_id
            );
            return group?.collection_id ?? data.collection_id;
        },
        get isError() {
            return collection.isError || hierarchy.isError;
        }
    };
};
