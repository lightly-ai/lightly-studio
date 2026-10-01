import { afterNavigate } from '$app/navigation';
import { usePostHog } from '$lib/hooks/usePostHog';

type SampleType = 'image' | 'video' | 'video_frame';

export const useTrackSampleInspected = (
    collectionId: () => string,
    sampleType: SampleType,
    isGridRoute: (routeId: string | null) => boolean
) => {
    const { trackEvent } = usePostHog();
    afterNavigate((nav) => {
        trackEvent('sample_inspected', {
            collection_id: collectionId(),
            sample_type: sampleType,
            opened_from: isGridRoute(nav.from?.route.id ?? null) ? 'grid' : 'direct_url'
        });
    });
};
