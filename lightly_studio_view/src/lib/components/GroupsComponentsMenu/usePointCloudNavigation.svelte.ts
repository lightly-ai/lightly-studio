import { goto } from '$app/navigation';
import { routeHelpers } from '$lib/routes';

interface NavigateParams {
    datasetId: string;
    collectionId: string;
    sampleId: string;
    groupId: string;
}

export function usePointCloudNavigation() {
    function navigate(params: NavigateParams): boolean {
        void goto(
            routeHelpers.toPointCloudLabeling({
                datasetId: params.datasetId,
                collectionType: 'group',
                collectionId: params.collectionId,
                // An MCAP component's sample is its sequence, so the sample id doubles as the sequence id.
                sequenceId: params.sampleId,
                groupId: params.groupId
            }),
            { invalidateAll: true }
        );
        return true;
    }

    return { navigate };
}
