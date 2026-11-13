import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { Bounds3 } from '../domain';
import type { SceneViewportProps } from './sceneViewportProps';

const EMPTY_BATCH: PointBatch = {
    positions: new Float32Array(0),
    intensities: new Float32Array(0),
    count: 0
};
const EMPTY_BOUNDS: Bounds3 = { min: [0, 0, 0], max: [0, 0, 0] };

const DEFAULTS = {
    batch: EMPTY_BATCH,
    colorMode: 'none',
    pointSize: 2,
    cuboids: [],
    annotationClasses: [],
    annotationSources: [],
    pointCloudBounds: EMPTY_BOUNDS,
    selectedAnnotationId: null,
    hoveredAnnotationId: null,
    activeTool: 'select',
    isEditingMode: false,
    draftCuboid: null,
    cameraMode: 'perspective',
    isScaleSource: false,
    showNavigationHelpers: true,
    showActiveBorder: false,
    viewState: null
} satisfies Partial<SceneViewportProps>;

type ResolvedSceneViewportProps = SceneViewportProps &
    Required<Pick<SceneViewportProps, keyof typeof DEFAULTS>>;

/** Resolves optional viewport inputs for canvas and overlay consumers. */
export function resolveSceneViewportProps(props: SceneViewportProps): ResolvedSceneViewportProps {
    // An input that is passed as undefined gets its default, like an input that is not passed.
    const defined = Object.fromEntries(
        Object.entries(props).filter(([, value]) => value !== undefined)
    ) as SceneViewportProps;
    return { ...DEFAULTS, ...defined };
}
