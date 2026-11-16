import { useThrelte } from '@threlte/core';
import { useOrbitControls } from '@threlte/extras';
import { onMount } from 'svelte';
import { get, writable, type Readable } from 'svelte/store';
import { Raycaster } from 'three';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
import type { useUpdateCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidAnnotation';
import { createFaceDrag, computePointerResize } from './cuboidFaceDrag';

type Face = Parameters<typeof createFaceDrag>[0]['face'];
type ResizePayload = Parameters<
    ReturnType<typeof useUpdateCuboidAnnotation>['handleCuboidTransform']
>[0];

interface Params {
    getAnnotation: () => Pick<CuboidAnnotation, 'id' | 'frameId' | 'center' | 'rotation' | 'size'>;
    onResizeStart?: () => void;
    onResizeCancel?: () => void;
    /**
     * Fires on every pointer move with the in-progress geometry. The consumer renders
     * the previewed annotation; the hook never scales the Three.js group itself, since
     * doing both would apply the resize twice and push the opposite face outward.
     */
    onResizePreview: (payload: ResizePayload) => void;
    onResizeEnd?: (payload: ResizePayload) => void;
}

interface FaceResizeReturn {
    hoveredFace: Readable<Face | null>;
    onFaceHoverEnter: (face: Face) => void;
    onFaceHoverLeave: () => void;
    onFacePointerDown: (
        params: Pick<Parameters<typeof createFaceDrag>[0], 'event' | 'face'>
    ) => void;
}

export function useCuboidFaceResize({
    getAnnotation,
    onResizeStart,
    onResizeCancel,
    onResizePreview,
    onResizeEnd
}: Params): FaceResizeReturn {
    const { camera, renderer } = useThrelte();
    const orbitControls = useOrbitControls();
    const canvas = renderer.domElement;
    const raycaster = new Raycaster();
    const hoveredFace = writable<Face | null>(null);
    let activeDrag: ReturnType<typeof createFaceDrag> | null = null;
    let lastTransform: ReturnType<typeof computePointerResize> = null;

    function onFaceHoverEnter(face: Face): void {
        if (activeDrag) return;
        hoveredFace.set(face);
        canvas.style.cursor = 'grab';
    }

    function onFaceHoverLeave(): void {
        if (activeDrag) return;
        hoveredFace.set(null);
        canvas.style.cursor = '';
    }

    const onFacePointerDown: FaceResizeReturn['onFacePointerDown'] = ({ event, face }) => {
        if (event.nativeEvent.button !== 0) return;
        onResizeStart?.();
        lastTransform = null;
        activeDrag = createFaceDrag({
            event,
            face,
            annotation: getAnnotation(),
            camera: camera.current
        });
        event.stopPropagation();
        // Keep TransformControls on the same element from taking pointer capture.
        event.nativeEvent.stopImmediatePropagation();
        canvas.setPointerCapture(event.nativeEvent.pointerId);
        canvas.style.cursor = 'grabbing';
        if (orbitControls.current) orbitControls.current.enabled = false;
    };

    function updateDrag(event: PointerEvent): void {
        if (!activeDrag) return;
        const transform = computePointerResize({
            event,
            canvas,
            camera: camera.current,
            drag: activeDrag,
            raycaster
        });
        if (!transform) return;
        lastTransform = transform;
        const { id, frameId, rotation } = getAnnotation();
        onResizePreview({ annotationId: id, frameId, ...transform, rotation });
    }

    function onPointerMove(event: PointerEvent): void {
        if (!activeDrag || event.pointerId !== activeDrag.pointerId) return;
        if (event.buttons === 0) {
            finalizeDrag();
            return;
        }
        // Block Threlte's bubble-phase listeners so no hover events fire during drag.
        event.stopImmediatePropagation();
        updateDrag(event);
    }

    function onPointerUp(event: PointerEvent): void {
        if (event.pointerId === activeDrag?.pointerId) {
            updateDrag(event);
            finalizeDrag();
        }
    }

    function onPointerCancel(event: PointerEvent): void {
        if (event.pointerId === activeDrag?.pointerId) cancelDrag();
    }

    function finishDrag(): void {
        if (!activeDrag) return;
        const { pointerId } = activeDrag;
        activeDrag = null;
        lastTransform = null;
        if (canvas.hasPointerCapture(pointerId)) canvas.releasePointerCapture(pointerId);
        if (orbitControls.current) orbitControls.current.enabled = true;
        canvas.style.cursor = get(hoveredFace) ? 'grab' : '';
    }

    function finalizeDrag(): void {
        if (activeDrag) {
            const { center, size } = lastTransform ?? {
                center: activeDrag.originalCenter,
                size: activeDrag.originalSize
            };
            const { id, frameId, rotation } = getAnnotation();
            onResizeEnd?.({ annotationId: id, frameId, center, rotation, size });
        } else {
            onResizeCancel?.();
        }
        finishDrag();
    }

    function cancelDrag(): void {
        if (!activeDrag) return;
        hoveredFace.set(null);
        onResizeCancel?.();
        finishDrag();
    }

    function onKeyDown(event: KeyboardEvent): void {
        if (event.key === 'Escape' && activeDrag) cancelDrag();
    }

    onMount(() => {
        canvas.addEventListener('pointermove', onPointerMove, { capture: true });
        canvas.addEventListener('pointerup', onPointerUp, { capture: true });
        canvas.addEventListener('pointercancel', onPointerCancel, { capture: true });
        canvas.addEventListener('lostpointercapture', onPointerCancel, { capture: true });
        window.addEventListener('keydown', onKeyDown);
        return () => {
            canvas.removeEventListener('pointermove', onPointerMove, { capture: true });
            canvas.removeEventListener('pointerup', onPointerUp, { capture: true });
            canvas.removeEventListener('pointercancel', onPointerCancel, { capture: true });
            canvas.removeEventListener('lostpointercapture', onPointerCancel, { capture: true });
            window.removeEventListener('keydown', onKeyDown);
            cancelDrag();
            canvas.style.cursor = '';
        };
    });

    return { hoveredFace, onFaceHoverEnter, onFaceHoverLeave, onFacePointerDown };
}
