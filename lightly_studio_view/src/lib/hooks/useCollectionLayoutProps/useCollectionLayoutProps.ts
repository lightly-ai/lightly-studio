import type { useRouteType } from '../useRouteType/useRouteType';

/**
 * Computes the props for CollectionLayout based on route type and plot visibility.
 */
export function useCollectionLayoutProps({
    routeType,
    showPlot,
    selectedCount,
    clearSelection
}: {
    routeType: ReturnType<typeof useRouteType>;
    showPlot: boolean;
    selectedCount: number;
    clearSelection: () => void;
}) {
    const showDetails = 
        routeType.isSampleDetails ||
            routeType.isAnnotationDetails ||
            routeType.isGroupDetails ||
            routeType.isVideoDetails;

    const showWithPlot = (routeType.isSamples || routeType.isVideos) && showPlot;

    const showGridHeader = 
        routeType.isSamples || routeType.isAnnotations || routeType.isVideos || routeType.isGroups;

    return {
        showDetails,
        showLeftSidebar: routeType.showLeftSidebar,
        showWithPlot,
        showGridHeader,
        showSelectionPill: routeType.showLeftSidebar,
        selectedCount,
        onClearSelection: clearSelection
    };
}
