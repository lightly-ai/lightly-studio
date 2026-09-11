import * as THREE from 'three';
import { createCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

type CuboidAnnotation = ReturnType<typeof createCuboidAnnotation>;
type Vector3 = CuboidAnnotation['center'];

interface CuboidDuplicateListenerParams {
    selectedAnnotation: CuboidAnnotation | null;
    oncreate: (cuboid: CuboidAnnotation) => void;
    onselect?: (annotationId: string | null) => void;
}

let duplicateId = 0;

function createDuplicateId(): string {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID();
    }
    duplicateId += 1;
    return `duplicate-${duplicateId}`;
}

/**
 * Computes the world-space center for a duplicate cuboid.
 *
 * The duplicate is offset from the original along its local +x axis (heading direction)
 * by the cuboid's full x-size, placing the copy adjacent without overlap.
 *
 * @param annotation - The source cuboid to duplicate.
 * @returns The world-space center for the duplicate cuboid.
 */
export function computeDuplicateCenter(annotation: CuboidAnnotation): Vector3 {
    const [qx, qy, qz, qw] = annotation.rotation;
    const localX = new THREE.Vector3(1, 0, 0).applyQuaternion(new THREE.Quaternion(qx, qy, qz, qw));
    const offset = annotation.size[0];
    return [
        annotation.center[0] + localX.x * offset,
        annotation.center[1] + localX.y * offset,
        annotation.center[2] + localX.z * offset
    ];
}

/**
 * Creates a duplicate cuboid offset along the original's local +x axis.
 *
 * The duplicate receives a new ID and retains the source annotation's properties.
 *
 * @param annotation - The source cuboid to duplicate.
 * @returns A complete cuboid suitable for passing to an `oncreate` callback.
 */
export function duplicateCuboid(annotation: CuboidAnnotation): CuboidAnnotation {
    return {
        id: createDuplicateId(),
        frameId: annotation.frameId,
        coordinateFrame: annotation.coordinateFrame,
        annotationClassId: annotation.annotationClassId,
        annotationSourceId: annotation.annotationSourceId,
        trackId: annotation.trackId,
        keyframeId: annotation.keyframeId,
        center: computeDuplicateCenter(annotation),
        size: annotation.size,
        rotation: annotation.rotation
    };
}

/**
 * Attaches a keydown handler that fires `oncreate` with a duplicate of the selected cuboid
 * when Ctrl+D (or Cmd+D on macOS) is pressed.
 *
 * @param params - Selected annotation and creation and selection callbacks.
 * @returns A function that removes the registered event listener.
 */
export function addCuboidDuplicateListeners({
    selectedAnnotation,
    oncreate,
    onselect
}: CuboidDuplicateListenerParams): () => void {
    function onKeyDown(event: KeyboardEvent): void {
        if (event.key === 'd' && (event.ctrlKey || event.metaKey) && selectedAnnotation) {
            event.preventDefault();
            const duplicate = duplicateCuboid(selectedAnnotation);
            oncreate(duplicate);
            onselect?.(duplicate.id);
        }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
}
