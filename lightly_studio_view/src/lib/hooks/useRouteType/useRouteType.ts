import { page } from '$app/state';
import {
    isAnnotationDetailsRoute,
    isAnnotationsRoute,
    isCaptionsRoute,
    isSampleDetailsRoute,
    isSamplesRoute,
    isVideoFramesRoute,
    isVideosRoute,
    isGroupsRoute,
    isGroupDetailsRoute,
    isVideoDetailsRoute
} from '$lib/routes';

/**
 * Hook to determine the current route type.
 * Centralizes all route detection logic in one place.
 */
export function useRouteType() {
    const routeId = page.route.id;

    const isSamples = isSamplesRoute(routeId);
    const isGroups = isGroupsRoute(routeId);
    const isGroupDetails = isGroupDetailsRoute(routeId);
    const isAnnotations = isAnnotationsRoute(routeId);
    const isSampleDetails = isSampleDetailsRoute(routeId);
    const isAnnotationDetails = isAnnotationDetailsRoute(routeId);
    const isCaptions = isCaptionsRoute(routeId);
    const isVideos = isVideosRoute(routeId);
    const isVideoFrames = isVideoFramesRoute(routeId);
    const isVideoDetails = isVideoDetailsRoute(routeId);

    const showLeftSidebar = 
        isSamples || isAnnotations || isVideos || isVideoFrames || isGroups;

    return {
        isSamples,
        isGroups,
        isGroupDetails,
        isAnnotations,
        isSampleDetails,
        isAnnotationDetails,
        isCaptions,
        isVideos,
        isVideoFrames,
        isVideoDetails,
        showLeftSidebar
    };
}
