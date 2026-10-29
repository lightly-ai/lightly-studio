import type { OrthographicCamera, PerspectiveCamera } from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { ColorMode } from '../pointCloudUtils';
import type { PointBatch } from '../types';
import type {
    CuboidAnnotation,
    CameraMode
} from '$lib/components/PointCloudLabelingWorkspace/domain';
import type { SceneViewState } from '../sceneViewState';
/** Point buffer appearance and camera synchronization inputs for the renderer. */
export interface PointCloudPointsProps {
    /** Point positions, intensities, and optional colors to render. */
    batch: PointBatch;
    /** Strategy used to color the point cloud. */
    colorMode: ColorMode;
    /** Screen-space point size in CSS pixels. */
    pointSize: number;
    /** Optional minimum and maximum intensity values used for coloring. */
    intensityRange?: [number, number];
    /** Refits the camera whenever this changes, e.g. when the coordinate frame changes. */
    fitKey?: string;
    /** Camera whose position and projection are controlled. */
    camera?: PerspectiveCamera | OrthographicCamera;
    /** Orbit controls supplying the shared scene target. */
    controls?: OrbitControls;
    /** Projection orientation used for rendering and editing. */
    cameraMode?: CameraMode;
    /** Selected cuboid defining the local object-view frame. */
    cameraCuboid?: CuboidAnnotation;
    /** Whether this viewport receives the user's edits; inactive object views follow them. */
    isActive?: () => boolean;
    /** Publishes the initial shared camera scale before other views synchronize. */
    isScaleSource?: boolean;
    /** Shared camera target and world-units-per-pixel scale. */
    viewState?: SceneViewState | null;
    /** Publishes camera navigation and scale changes to sibling views. */
    onViewStateChange?: (viewState: SceneViewState) => void;
}
