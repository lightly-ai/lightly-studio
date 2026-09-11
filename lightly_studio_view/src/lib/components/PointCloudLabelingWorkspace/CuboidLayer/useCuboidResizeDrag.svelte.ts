import { Plane, Vector3 } from 'three';
import type { Camera, Group, WebGLRenderer } from 'three';
import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { applyResizeDelta, buildDragPlane, getWorldFaceCenter, getWorldFaceNormal } from './cuboidResize';
import { buildPointerRay, hitFacePlane } from './cuboidResizeFaces';
import type { CuboidAnnotation, CuboidHandle } from '$lib/components/PointCloudLabelingWorkspace/domain';

/**
 * Manages pointer-capture drag state for cuboid face resizing.
 *
 * All params are getter functions so the handlers always read current values
 * (props change between when the $effect runs and when an event fires).
 *
 * Returns reactive `previewAnnotation`, `hoveredHandle`, and `activeDragHandle`
 * via getters so callers automatically update when these change.
 */
export function useCuboidResizeDrag({
    getAnnotation,
    getOrbitControls,
    getCamera,
    getRenderer,
    getFacePlanesGroup,
    getOnhover,
    getOncuboidupdate
}: {
    getAnnotation: () => CuboidAnnotation;
    getOrbitControls: () => ThreeOrbitControls | undefined;
    getCamera: () => Camera;
    getRenderer: () => WebGLRenderer;
    getFacePlanesGroup: () => Group | undefined;
    getOnhover: () => ((annotationId: string | null, handle: CuboidHandle | null) => void) | undefined;
    getOncuboidupdate: () => ((cuboid: CuboidAnnotation) => void) | undefined;
}) {
    let previewAnnotation = $state<CuboidAnnotation>(getAnnotation());
    let hoveredHandle = $state<CuboidHandle | null>(null);
    let activeDragHandle = $state<CuboidHandle | null>(null);
    let dragPlane: Plane | null = null;
    let dragStartPoint = new Vector3();
    let dragWorldFaceNormal = new Vector3();
    let dragStartAnnotation: CuboidAnnotation | null = null;

    $effect(() => {
        const annotation = getAnnotation();
        if (!activeDragHandle) previewAnnotation = annotation;
    });

    $effect(() => {
        const domElement = getRenderer().domElement;

        function endDrag(event: PointerEvent): void {
            getOncuboidupdate()?.(previewAnnotation);
            domElement.releasePointerCapture(event.pointerId);
            const orbitControls = getOrbitControls();
            if (orbitControls) orbitControls.enabled = true;
            activeDragHandle = null;
            dragPlane = null;
            dragStartAnnotation = null;
            hoveredHandle = null;
            getOnhover()?.(null, null);
        }

        function onPointerMove(event: PointerEvent): void {
            const camera = getCamera();
            const renderer = getRenderer();
            if (activeDragHandle) {
                if (event.buttons === 0) { endDrag(event); return; }
                if (!dragPlane || !dragStartAnnotation) return;
                const currentPoint = new Vector3();
                if (!buildPointerRay(event, camera, renderer).intersectPlane(dragPlane, currentPoint)) return;
                const displacement = currentPoint.sub(dragStartPoint).dot(dragWorldFaceNormal);
                previewAnnotation = applyResizeDelta(dragStartAnnotation, activeDragHandle, displacement);
            } else {
                const facePlanesGroup = getFacePlanesGroup();
                const handle = facePlanesGroup
                    ? hitFacePlane(facePlanesGroup, event, camera, renderer)
                    : null;
                if (handle !== hoveredHandle) {
                    hoveredHandle = handle;
                    getOnhover()?.(handle ? getAnnotation().id : null, handle);
                }
            }
        }

        function onPointerDown(event: PointerEvent): void {
            const facePlanesGroup = getFacePlanesGroup();
            if (!facePlanesGroup) return;
            const camera = getCamera();
            const renderer = getRenderer();
            const handle = hitFacePlane(facePlanesGroup, event, camera, renderer);
            if (!handle) return;
            // Capture phase: block OrbitControls (bubble phase) from starting orbit.
            event.stopImmediatePropagation();
            const annotation = getAnnotation();
            activeDragHandle = handle;
            hoveredHandle = handle;
            dragStartAnnotation = annotation;
            dragWorldFaceNormal = getWorldFaceNormal(handle, annotation.rotation);
            dragPlane = buildDragPlane(
                camera.getWorldDirection(new Vector3()),
                getWorldFaceCenter(handle, annotation)
            );
            buildPointerRay(event, camera, renderer).intersectPlane(dragPlane, dragStartPoint);
            domElement.setPointerCapture(event.pointerId);
            if (getOrbitControls()) getOrbitControls()!.enabled = false;
        }

        function onPointerUp(event: PointerEvent): void {
            if (activeDragHandle) endDrag(event);
        }

        domElement.addEventListener('pointermove', onPointerMove);
        domElement.addEventListener('pointerdown', onPointerDown, { capture: true });
        domElement.addEventListener('pointerup', onPointerUp);
        return () => {
            domElement.removeEventListener('pointermove', onPointerMove);
            domElement.removeEventListener('pointerdown', onPointerDown, { capture: true });
            domElement.removeEventListener('pointerup', onPointerUp);
        };
    });

    return {
        get previewAnnotation() { return previewAnnotation; },
        get hoveredHandle() { return hoveredHandle; },
        get activeDragHandle() { return activeDragHandle; }
    };
}
