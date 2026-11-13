import { SampleType } from '$lib/api/lightly_studio_local';
import {
    readCollectionHierarchyOptions,
    readCollectionOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

/**
 * Collections whose annotation sources hang off a child instead of themselves, by the sample
 * type of the collection on screen and the sample type of that child.
 */
const OWNER_CHILD_SAMPLE_TYPE: Partial<Record<SampleType, SampleType>> = {
    // On the point-cloud grid the collection on screen is an MCAP SEQUENCE, and its GROUP child
    // owns the sources.
    [SampleType.SEQUENCE]: SampleType.GROUP,
    // Video annotations are attached to frames, so a video dataset keeps its sources under the
    // VIDEO_FRAME child, not under the VIDEO collection the videos grid points at.
    [SampleType.VIDEO]: SampleType.VIDEO_FRAME
};

/**
 * The collection that owns the annotation sources of the collection on screen. Annotation
 * sources are child collections of the owner, so on the annotations grid, where the collection
 * on screen is a source, the owner is its parent. On the videos and point-cloud grids the owner
 * is a child of the collection on screen, see `OWNER_CHILD_SAMPLE_TYPE`. Undefined while the
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
        enabled: !!(collection.data && OWNER_CHILD_SAMPLE_TYPE[collection.data.sample_type])
    }));

    return {
        get ownerCollectionId() {
            const data = collection.data;
            if (!data) return undefined;
            if (data.sample_type === SampleType.ANNOTATION) {
                return data.parent_collection_id ?? undefined;
            }
            const childSampleType = OWNER_CHILD_SAMPLE_TYPE[data.sample_type];
            if (!childSampleType) return data.collection_id;
            if (!hierarchy.data) return undefined;
            const child = hierarchy.data.find(
                (candidate) =>
                    candidate.sample_type === childSampleType &&
                    candidate.parent_collection_id === data.collection_id
            );
            return child?.collection_id ?? data.collection_id;
        },
        get isError() {
            return collection.isError || hierarchy.isError;
        }
    };
};
