import type { CollectionView } from '$lib/api/lightly_studio_local';
import { routeHelpers } from '$lib/routes';

interface GetWorkspaceSourcePathParams {
    datasetId: string;
    collection: Pick<CollectionView, 'collection_id' | 'name' | 'sample_type'>;
    /** Collection type of the grid the user came from; `group` when opened from a group. */
    collectionType?: string;
}

/**
 * Builds the Home -> collection -> sequence breadcrumb for the point-cloud labeling workspace,
 * linking the collection back to the grid the sequence was opened from.
 */
export function getWorkspaceSourcePath({
    datasetId,
    collection,
    collectionType
}: GetWorkspaceSourcePathParams): { label: string; href?: string }[] {
    const type = collectionType ?? collection.sample_type.toLowerCase();
    const collectionHref =
        type === 'group'
            ? routeHelpers.toGroups(datasetId, type, collection.collection_id)
            : routeHelpers.toPointClouds(datasetId, type, collection.collection_id);

    return [
        { label: 'Home', href: routeHelpers.toHome() },
        { label: collection.name, href: collectionHref },
        { label: 'Sequence' }
    ];
}
