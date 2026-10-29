import { getContext, setContext } from 'svelte';
import type { AnnotationClass, CameraMode, WorkspaceTool } from '../domain';
import type { createCuboidTransformState } from './cuboidTransformState';
import type { createCuboidHoverTracker } from './cuboidHoverTracker';
import type { CuboidLayerProps } from './cuboidLayerProps';
/** Editing and selection state shared by cuboids rendered in one viewport. */
interface CuboidLayerState {
    /** Annotation classes used to color cuboids. */
    annotationClasses: readonly AnnotationClass[];
    /** Shared working transforms and persistence. */
    transforms: ReturnType<typeof createCuboidTransformState>;
    /** Tool currently selected for editing. */
    activeTool: WorkspaceTool;
    /** Camera orientation used to choose editing handles. */
    cameraMode: CameraMode;
    /** Tracks overlapping hover and selection hits. */
    hoverTracker: ReturnType<typeof createCuboidHoverTracker>;
    /** Selected annotation, or null. */
    selectedAnnotationId: string | null;
    /** Hovered annotation, or null. */
    hoveredAnnotationId: string | null;
    /** Selects an annotation after hit arbitration. */
    onselect?: (id: string | null) => void;
    /** Reports a completed gizmo transform before it is committed. */
    onCuboidTransform?: CuboidLayerProps['onCuboidTransform'];
}
const KEY = Symbol('cuboid-layer');
/** Provides one viewport's cuboid interaction state. */
export function provideCuboidLayerContext(getState: () => CuboidLayerState): void {
    setContext(KEY, getState);
}
/** Reads cuboid interaction state from the containing layer. */
export function useCuboidLayerContext(): () => CuboidLayerState {
    const context = getContext<(() => CuboidLayerState) | undefined>(KEY);
    if (!context) throw new Error('Cuboid layer context is missing.');
    return context;
}
