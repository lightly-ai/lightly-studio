import { isFrameDetailsRoute } from '$lib/routes';

interface IsAssistedLabelingViewParams {
    isOnAnnotationDetailsView: boolean | undefined;
    routeId: string | null;
}

// Assisted labeling supports images only, not video frames, and the annotation details view
// only edits.
export const isAssistedLabelingView = ({
    isOnAnnotationDetailsView,
    routeId
}: IsAssistedLabelingViewParams): boolean =>
    !isOnAnnotationDetailsView && !isFrameDetailsRoute(routeId);
