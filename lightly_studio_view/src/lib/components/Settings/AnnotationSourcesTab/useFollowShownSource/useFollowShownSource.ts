import { goto } from '$app/navigation';
import { page } from '$app/state';
import { routeHelpers } from '$lib/routes';

interface Params {
    /** The collection of the route. On the annotations grid it is the source on screen. */
    routeCollectionId: string;
}

interface DeletedSource {
    sourceId: string;
    /** The collection the deleted source belonged to. */
    collectionId: string;
}

/**
 * Moves the annotations grid off a source that the tab deleted, to the collection the source
 * belonged to, so the route does not point at a collection that no longer exists. Reloads the
 * route data. `afterDelete` resolves once the navigation is done, so the caller can refresh the
 * queries only after the grid has left.
 */
export const useFollowShownSource = (getParams: () => Params) => {
    const datasetId = () => page.params.dataset_id ?? '';

    return {
        afterDelete: ({ sourceId, collectionId }: DeletedSource): Promise<void> => {
            if (sourceId !== getParams().routeCollectionId) return Promise.resolve();
            // The collection layout redirects to the collection's own collection type.
            const collectionType = page.params.collection_type ?? 'image';
            return goto(routeHelpers.toCollectionHome(datasetId(), collectionType, collectionId), {
                invalidateAll: true
            });
        }
    };
};
