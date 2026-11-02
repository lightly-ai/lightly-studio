import type { Snippet } from 'svelte';
import type { ColorMode, PointBatch, SceneViewState } from '$lib/components/PointCloudViewer';
import type {
    AnnotationClass,
    AnnotationSource,
    Bounds3,
    CuboidAnnotation,
    CuboidHandle,
    Vector3,
    CameraMode,
    WorkspaceTool
} from '../domain';
import type { createCuboidTransformState } from '../CuboidLayer/cuboidTransformState';
import type { CuboidLayerProps } from '../CuboidLayer/cuboidLayerProps';
/** Rendering inputs and interaction callbacks for a reusable scene viewport. */
export interface SceneViewportProps {
    /** Optional header rendered inside the viewport focus boundary. */
    header?: Snippet;
    /** Optional editing controls anchored inside the viewport. */
    tools?: Snippet;
    /** Point positions and intensities consumed by the existing renderer. */
    batch?: PointBatch;
    /** Strategy used to color the point cloud. */
    colorMode?: ColorMode;
    /** Screen-space point size in CSS pixels. */
    pointSize?: number;
    /** Optional minimum and maximum intensity values used for coloring. */
    intensityRange?: [number, number];
    /** Cuboid annotations rendered over the point cloud (typically the transform overlay). */
    cuboids?: readonly CuboidAnnotation[];
    /** Annotation classes and colors used to render cuboids. */
    annotationClasses?: readonly AnnotationClass[];
    /** Available annotation sources for the active sequence. */
    annotationSources?: readonly AnnotationSource[];
    /** Transform state shared with the parent; drives the gizmo and face-resize interactions. */
    transforms: ReturnType<typeof createCuboidTransformState>;
    /** World-space bounds for initial camera and ground placement. */
    pointCloudBounds?: Bounds3;
    /** Refits the camera whenever this changes, e.g. when the coordinate frame changes. */
    fitKey?: string;
    /** Identity of the currently selected cuboid, or null. */
    selectedAnnotationId?: string | null;
    /** Identity of the currently hovered cuboid, or null. */
    hoveredAnnotationId?: string | null;
    /** Tool that determines whether cuboids can be selected. */
    activeTool?: WorkspaceTool;
    /** Projection orientation used for rendering and editing. */
    cameraMode?: CameraMode;
    /** Publishes the initial shared camera scale before other views synchronize. */
    isScaleSource?: boolean;
    /** Whether navigation buttons and shortcut hints are shown. */
    showNavigationHelpers?: boolean;
    /** Whether hovered annotation metadata is shown in this viewport. */
    showAnnotationTooltips?: boolean;
    /** Shows the subtle active-view border in multi-view layouts. */
    showActiveBorder?: boolean;
    /** Fires when the user selects or deselects a cuboid. */
    onselect?: (annotationId: string | null) => void;
    /** Fires when the pointer enters or leaves a cuboid. */
    onhover?: (annotationId: string | null, handle: CuboidHandle | null) => void;
    /** Fires when the user clicks the ground plane in create-cuboid mode. */
    onCreateCuboid?: (position: Vector3) => void;
    /** Reports a completed annotation gizmo transform before it is committed. */
    onCuboidTransform?: CuboidLayerProps['onCuboidTransform'];
    /** Fires on the left arrow key. */
    onPreviousTick?: () => void;
    /** Fires on the right arrow key. */
    onNextTick?: () => void;
    /** Shared camera target and world-units-per-pixel scale. */
    viewState?: SceneViewState | null;
    /** Publishes camera navigation and scale changes to sibling views. */
    onViewStateChange?: (viewState: SceneViewState) => void;
}
