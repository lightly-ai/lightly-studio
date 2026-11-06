import { goto } from '$app/navigation';
import { page } from '$app/state';
import { routeHelpers } from '$lib/routes';

interface Params {
    /** The collection of the route. On the annotations grid it is the source on screen. */
    routeCollectionId: string;
    /** The collection that owns the annotation sources. */
    ownerCollectionId: string;
}

/**
 * Moves the annotations grid off a source that the tab deleted, so the route does not point at
 * a collection that no longer exists. Reloads the route data.
 */
export const useFollowShownSource = (getParams: () => Params) => {
    const isShown = (sourceId: string) => sourceId === getParams().routeCollectionId;
    const datasetId = () => page.params.dataset_id ?? '';

    return {
        afterDelete: (sourceId: string) => {
            if (!isShown(sourceId)) return;
            // The collection layout redirects to the owner's own collection type.
            const collectionType = page.params.collection_type ?? 'image';
            goto(
                routeHelpers.toCollectionHome(
                    datasetId(),
                    collectionType,
                    getParams().ownerCollectionId
                ),
                { invalidateAll: true }
            );
        }
    };
};
