import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { Bounds3 } from '../domain';
import type { SceneViewportProps } from './sceneViewportProps';

const EMPTY_BATCH: PointBatch = {
    positions: new Float32Array(0),
    intensities: new Float32Array(0),
    count: 0
};
const EMPTY_BOUNDS: Bounds3 = { min: [0, 0, 0], max: [0, 0, 0] };

/** Resolves optional viewport inputs for canvas and overlay consumers. */
export function resolveSceneViewportProps({
    header,
    tools,
    batch = EMPTY_BATCH,
    colorMode = 'none',
    pointSize = 2,
    intensityRange,
    cuboids = [],
    annotationClasses = [],
    annotationSources = [],
    transforms,
    pointCloudBounds = EMPTY_BOUNDS,
    fitKey,
    selectedAnnotationId = null,
    hoveredAnnotationId = null,
    activeTool = 'select',
    onselect,
    onhover,
    onCreateCuboid,
    onCuboidTransform,
    onPreviousTick,
    onNextTick,
    cameraMode = 'perspective',
    isScaleSource = false,
    showNavigationHelpers = true,
    showAnnotationTooltips = true,
    showActiveBorder = false,
    viewState = null,
    onViewStateChange
}: SceneViewportProps) {
    return {
        header,
        tools,
        batch,
        colorMode,
        pointSize,
        intensityRange,
        cuboids,
        annotationClasses,
        annotationSources,
        transforms,
        pointCloudBounds,
        fitKey,
        selectedAnnotationId,
        hoveredAnnotationId,
        activeTool,
        onselect,
        onhover,
        onCreateCuboid,
        onCuboidTransform,
        onPreviousTick,
        onNextTick,
        cameraMode,
        isScaleSource,
        showNavigationHelpers,
        showAnnotationTooltips,
        showActiveBorder,
        viewState,
        onViewStateChange
    };
}
