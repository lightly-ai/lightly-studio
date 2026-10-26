import type { ColorMode } from './pointCloudUtils';
import type { PointBatch } from './types';
import type { CameraMode, WorkspaceTool } from '$lib/components/PointCloudLabelingWorkspace/domain';
import type { SceneViewState } from './sceneViewState';
/** Point data, camera configuration, and navigation bindings for a 3D scene. */
export interface PointCloudSceneProps {
    /** Current point cloud batch with positions, intensities, and count. */
    batch: PointBatch;
    /** How points are colored: by height, intensity, per-point rgb, or neutral gray. */
    colorMode?: ColorMode;
    /** Screen-space point size in pixels. */
    pointSize?: number;
    /** Min/max clamp for intensity-based coloring. */
    intensityRange?: [number, number];
    /** Refits the camera whenever this changes, e.g. when the coordinate frame changes. */
    fitKey?: string;
    /** Tool that determines whether orbit rotation is enabled. */
    activeTool?: WorkspaceTool;
    /** Projection orientation used for rendering and editing. */
    cameraMode?: CameraMode;
    /** Publishes the initial shared camera scale before other views synchronize. */
    isScaleSource?: boolean;
    /** Whether this viewport currently owns navigation input. */
    isActive?: () => boolean;
    /** Identifies the viewport receiving navigation commands. */
    navigationId?: symbol;
    /** Shared camera target and world-units-per-pixel scale. */
    viewState?: SceneViewState | null;
    /** Publishes camera navigation and scale changes to sibling views. */
    onViewStateChange?: (viewState: SceneViewState) => void;
}
