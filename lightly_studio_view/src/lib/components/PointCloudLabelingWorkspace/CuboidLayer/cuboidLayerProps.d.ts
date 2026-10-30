import type * as Domain from '../domain';
import type { createCuboidTransformState } from './cuboidTransformState';
/** Annotation rendering and editing inputs for one viewport's cuboid layer. */
export interface CuboidLayerProps {
    /** Cuboid annotations rendered in this viewport. */
    cuboids: readonly Domain.CuboidAnnotation[];
    /** Annotation classes and colors used to render cuboids. */
    annotationClasses: readonly Domain.AnnotationClass[];
    /** Shared annotation transforms and their persistence actions. */
    transforms: ReturnType<typeof createCuboidTransformState>;
    /** Selected annotation identifier, or null. */
    selectedAnnotationId?: string | null;
    /** Hovered annotation identifier, or null. */
    hoveredAnnotationId?: string | null;
    /** Tool selected in the main scene toolbar. */
    activeTool?: Domain.WorkspaceTool;
    /** Projection orientation used for rendering and editing. */
    cameraMode?: Domain.CameraMode;
    /** Retained cloud bounds used for ground placement and creation. */
    groundPlaneBounds: Domain.Bounds3;
    /** Selects or clears an annotation after hit testing. */
    onselect?: (annotationId: string | null) => void;
    /** Updates hovered annotation and handle feedback. */
    onhover?: (annotationId: string | null, handle: Domain.CuboidHandle | null) => void;
    /** Creates an annotation at a world-space placement point. */
    onCreateCuboid?: (position: Domain.Vector3) => void;
    /** Reports a completed gizmo transform before it is committed. */
    onCuboidTransform?: (
        payload: Parameters<ReturnType<typeof createCuboidTransformState>['commit']>[0]
    ) => void;
}
