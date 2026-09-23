import { get } from 'svelte/store';
import { goto } from '$app/navigation';
import { useFeatureFlags } from '$lib/hooks';
import { routeHelpers } from '$lib/routes';

// Kept in sync with lightly_studio/api/features.py and the point-clouds route's own copy of
// this constant. Off by default: until it is enabled, MCAP components stay non-interactive
// exactly as before, so the existing sample detail view is unaffected.
const POINT_CLOUD_LABELING_FEATURE = 'point_cloud_labeling';

interface NavigateParams {
    datasetId: string;
    collectionId: string;
    sampleId: string;
    groupId: string;
}

export function usePointCloudNavigation() {
    const { featureFlags } = useFeatureFlags();

    function navigate(params: NavigateParams): boolean {
        if (!get(featureFlags).includes(POINT_CLOUD_LABELING_FEATURE)) return false;
        void goto(
            routeHelpers.toPointCloudLabeling({
                datasetId: params.datasetId,
                collectionType: 'group',
                collectionId: params.collectionId,
                sampleId: params.sampleId,
                groupId: params.groupId
            }),
            { invalidateAll: true }
        );
        return true;
    }

    return { navigate };
}
