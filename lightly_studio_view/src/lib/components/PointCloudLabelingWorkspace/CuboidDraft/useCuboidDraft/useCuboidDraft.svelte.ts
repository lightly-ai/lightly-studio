import { useThrelte } from '@threlte/core';
import { onMount } from 'svelte';
import { Plane, Raycaster, Vector2, Vector3 as ThreeVector3, type Camera } from 'three';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { CameraMode, Vector3 } from '$lib/components/PointCloudLabelingWorkspace/domain';
import {
    getDraftBox,
    getDraftRectangle,
    getFootprintBox,
    getFootprintWidth,
    getHeightExtent,
    getMissingAxis,
    hasAngledFootprint,
    isDrag,
    type CuboidBox,
    type DraftFootprint,
    type ScreenPoint
} from '../cuboidDraft';
import { fitFootprintHeight, fitMissingAxis } from '../fitCuboidToPoints';

interface PlanePointerEvent {
    /** World-space hit on the plane mesh. */
    point: { x: number; y: number; z: number };
    nativeEvent: PointerEvent;
}

interface Params {
    getCameraMode: () => CameraMode;
    getBatch: () => PointBatch | undefined;
    /** Timeline tick on display. The batch stays the same while the next tick loads. */
    getTick: () => number | undefined;
    onCreate: (box: CuboidBox) => void;
}

interface CuboidDraftReturn {
    /** Box to preview, or null when no draft is visible. */
    readonly previewBox: CuboidBox | null;
    handlePlanePointerDown: (event: PlanePointerEvent) => void;
}

/**
 * Step of a draft. Side and front views draw one `rectangle` with a drag. Top and 3D views draw
 * the first `side` (heading and length), then the `width`, and the 3D view then the `height`.
 */
type DraftStep = 'rectangle' | 'side' | 'width' | 'height';

interface Draft {
    pointerId: number;
    cameraMode: CameraMode;
    batch: PointBatch | undefined;
    tick: number | undefined;
    plane: Plane;
    step: DraftStep;
    /** True from the first pointer-down until its release. */
    isPressed: boolean;
    startScreen: ScreenPoint;
    startWorld: Vector3;
    currentScreen: ScreenPoint;
    currentWorld: Vector3;
    /** Signed width of the footprint, set in the width step. */
    width: number;
}

/** Below this horizontal view length the height plane is almost parallel to the rays. */
const MIN_HORIZONTAL_VIEW_LENGTH = 1e-3;

const CANVAS_EVENTS = [
    'pointerdown',
    'pointermove',
    'pointerup',
    'pointercancel',
    'lostpointercapture'
] as const;

export function useCuboidDraft({
    getCameraMode,
    getBatch,
    getTick,
    onCreate
}: Params): CuboidDraftReturn {
    const { camera, renderer } = useThrelte();
    const canvas = renderer.domElement;
    const raycaster = new Raycaster();
    let draft: Draft | null = null;
    let previewBox = $state<CuboidBox | null>(null);
    /** Click that ended a draft; it also reaches the plane mesh and must not start a new draft. */
    let finishingClick: PointerEvent | null = null;

    function handlePlanePointerDown({ point, nativeEvent }: PlanePointerEvent): void {
        // While a draft is active, its clicks arrive through the canvas listeners.
        if (nativeEvent.button !== 0 || draft || nativeEvent === finishingClick) return;
        if (hasCameraModifier(nativeEvent)) return;
        const cameraMode = getCameraMode();
        const startWorld: Vector3 = [point.x, point.y, point.z];
        const startScreen = { x: nativeEvent.clientX, y: nativeEvent.clientY };
        draft = {
            pointerId: nativeEvent.pointerId,
            cameraMode,
            batch: getBatch(),
            tick: getTick(),
            plane: createDraftPlane(cameraMode, startWorld),
            step: hasAngledFootprint(cameraMode) ? 'side' : 'rectangle',
            isPressed: true,
            startScreen,
            startWorld,
            currentScreen: startScreen,
            currentWorld: startWorld,
            width: 0
        };
        // Capture works because OrbitControls registers its listener before interactivity(),
        // as in useCuboidFaceResize.
        canvas.setPointerCapture(nativeEvent.pointerId);
        addListeners();
    }

    function getFootprint(active: Draft): DraftFootprint {
        return { start: active.startWorld, end: active.currentWorld, width: active.width };
    }

    /** True when the pointer is far enough from the first point to define a side or rectangle. */
    function hasExtent(active: Draft): boolean {
        return isDrag(active.startScreen, active.currentScreen);
    }

    function raycastPlane(event: PointerEvent, plane: Plane): ThreeVector3 | null {
        const rect = canvas.getBoundingClientRect();
        const ndc = new Vector2(
            ((event.clientX - rect.left) / rect.width) * 2 - 1,
            -((event.clientY - rect.top) / rect.height) * 2 + 1
        );
        raycaster.setFromCamera(ndc, camera.current);
        return raycaster.ray.intersectPlane(plane, new ThreeVector3());
    }

    /** Moves the second point of the rectangle or of the first side. */
    function updateEnd(active: Draft, event: PointerEvent): void {
        active.currentScreen = { x: event.clientX, y: event.clientY };
        if (!hasExtent(active)) {
            previewBox = null;
            return;
        }
        const hit = raycastPlane(event, active.plane);
        if (!hit) return;
        active.currentWorld = [hit.x, hit.y, hit.z];
        previewBox =
            active.step === 'side'
                ? getFootprintBox(getFootprint(active))
                : getDraftBox(
                      getDraftRectangle(active.cameraMode, active.startWorld, active.currentWorld)
                  );
    }

    function updateWidth(active: Draft, event: PointerEvent): void {
        const hit = raycastPlane(event, active.plane);
        if (!hit) return;
        active.width = getFootprintWidth(getFootprint(active), [hit.x, hit.y, hit.z]);
        previewBox = getFootprintBox(getFootprint(active));
    }

    function updateHeight(active: Draft, event: PointerEvent): void {
        const footprint = getFootprint(active);
        const plane = createHeightPlane(getFootprintBox(footprint).center, camera.current);
        const hit = plane && raycastPlane(event, plane);
        if (!hit) return;
        previewBox = getFootprintBox(footprint, getHeightExtent(active.startWorld[2], hit.z));
    }

    function update(active: Draft, event: PointerEvent): void {
        if (active.step === 'width') updateWidth(active, event);
        else if (active.step === 'height') updateHeight(active, event);
        else updateEnd(active, event);
    }

    function finish(box: CuboidBox | null): void {
        discardDraft();
        if (box) onCreate(box);
    }

    /** Fixes the current step with a release or a click and moves to the next one. */
    function confirmStep(active: Draft): void {
        if (active.step === 'rectangle') {
            // A drag whose rays never hit the plane has no rectangle to create.
            if (!hasExtent(active) || !previewBox) return finish(null);
            const rectangle = getDraftRectangle(
                active.cameraMode,
                active.startWorld,
                active.currentWorld
            );
            return finish(getDraftBox(rectangle, fitMissingAxis(rectangle, active.batch)));
        }
        if (active.step === 'side') {
            // Without a side yet, the next click sets its end.
            if (hasExtent(active) && previewBox) active.step = 'width';
            return;
        }
        const footprint = getFootprint(active);
        if (active.step === 'width' && active.cameraMode === 'perspective') {
            active.step = 'height';
            return;
        }
        if (active.step === 'width') {
            return finish(getFootprintBox(footprint, fitFootprintHeight(footprint, active.batch)));
        }
        finish(previewBox);
    }

    function onPointerMove(event: PointerEvent): void {
        if (!draft || (draft.isPressed && event.pointerId !== draft.pointerId)) return;
        update(draft, event);
    }

    function onPointerUp(event: PointerEvent): void {
        if (!draft?.isPressed || event.pointerId !== draft.pointerId) return;
        draft.isPressed = false;
        update(draft, event);
        confirmStep(draft);
    }

    function onPointerDown(event: PointerEvent): void {
        // The pointer-down that started the draft is still pressed.
        if (!draft || draft.isPressed) return;
        if (event.button === 2) discardDraft();
        if (event.button !== 0 || hasCameraModifier(event)) return;
        finishingClick = event;
        update(draft, event);
        confirmStep(draft);
    }

    function onContextMenu(event: Event): void {
        event.preventDefault();
        discardDraft();
    }

    function onKeyDown(event: KeyboardEvent): void {
        if (event.key === 'Escape') discardDraft();
    }

    function onCanvasEvent(event: Event): void {
        const pointerEvent = event as PointerEvent;
        if (event.type === 'pointerdown') onPointerDown(pointerEvent);
        else if (event.type === 'pointermove') onPointerMove(pointerEvent);
        else if (event.type === 'pointerup') onPointerUp(pointerEvent);
        // A cancel or a capture loss of a different pointer must not end this draft.
        else if (pointerEvent.pointerId !== draft?.pointerId) return;
        // A release ends the pointer capture; the steps after it go on without capture.
        else if (event.type !== 'lostpointercapture' || draft?.isPressed) discardDraft();
    }

    function addListeners(): void {
        for (const type of CANVAS_EVENTS) canvas.addEventListener(type, onCanvasEvent);
        canvas.addEventListener('contextmenu', onContextMenu);
        window.addEventListener('keydown', onKeyDown);
    }

    function removeListeners(): void {
        for (const type of CANVAS_EVENTS) canvas.removeEventListener(type, onCanvasEvent);
        canvas.removeEventListener('contextmenu', onContextMenu);
        window.removeEventListener('keydown', onKeyDown);
    }

    function discardDraft(): void {
        if (!draft) return;
        const { pointerId } = draft;
        draft = null;
        previewBox = null;
        removeListeners();
        if (canvas.hasPointerCapture(pointerId)) canvas.releasePointerCapture(pointerId);
    }

    $effect(() => {
        const batch = getBatch();
        const tick = getTick();
        if (draft && (batch !== draft.batch || tick !== draft.tick)) discardDraft();
    });

    onMount(() => discardDraft);

    return {
        get previewBox() {
            return previewBox;
        },
        handlePlanePointerDown
    };
}

/** OrbitControls pans on a modifier + left-drag, so those pointer-downs belong to the camera. */
function hasCameraModifier(event: PointerEvent): boolean {
    return event.shiftKey || event.ctrlKey || event.metaKey;
}

function createDraftPlane(cameraMode: CameraMode, startWorld: Vector3): Plane {
    const normal = new ThreeVector3();
    normal.setComponent(getMissingAxis(cameraMode), 1);
    return new Plane().setFromNormalAndCoplanarPoint(normal, new ThreeVector3(...startWorld));
}

/** Vertical plane through the footprint centre facing the camera; null when looking almost straight down. */
function createHeightPlane(centre: Vector3, camera: Camera): Plane | null {
    const normal = camera.getWorldDirection(new ThreeVector3()).setZ(0);
    if (normal.length() < MIN_HORIZONTAL_VIEW_LENGTH) return null;
    return new Plane().setFromNormalAndCoplanarPoint(
        normal.normalize(),
        new ThreeVector3(...centre)
    );
}
