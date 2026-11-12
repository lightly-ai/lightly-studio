import { useThrelte } from '@threlte/core';
import { onMount } from 'svelte';
import { Plane, Raycaster, Vector2, Vector3 as ThreeVector3 } from 'three';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { CameraMode, Vector3 } from '$lib/components/PointCloudLabelingWorkspace/domain';
import {
    getDraftBox,
    getDraftRectangle,
    getMissingAxis,
    isDrag,
    type CuboidBox,
    type CuboidPlacement,
    type ScreenPoint
} from '../cuboidDraft';
import { fitMissingAxis } from '../fitCuboidToPoints';

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
    onCreate: (placement: CuboidPlacement) => void;
}

interface CuboidDraftReturn {
    /** Box to preview, or null when no drag is active. */
    readonly previewBox: CuboidBox | null;
    handlePlanePointerDown: (event: PlanePointerEvent) => void;
}

interface Draft {
    pointerId: number;
    cameraMode: CameraMode;
    batch: PointBatch | undefined;
    tick: number | undefined;
    plane: Plane;
    startScreen: ScreenPoint;
    startWorld: Vector3;
    currentScreen: ScreenPoint;
    currentWorld: Vector3;
}

const CANVAS_EVENTS = ['pointermove', 'pointerup', 'pointercancel', 'lostpointercapture'] as const;

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

    function handlePlanePointerDown({ point, nativeEvent }: PlanePointerEvent): void {
        if (nativeEvent.button !== 0) return;
        // OrbitControls pans on a modifier + left-drag, so leave those to the camera.
        if (nativeEvent.shiftKey || nativeEvent.ctrlKey || nativeEvent.metaKey) return;
        discardDraft();
        const cameraMode = getCameraMode();
        const startWorld: Vector3 = [point.x, point.y, point.z];
        const startScreen = { x: nativeEvent.clientX, y: nativeEvent.clientY };
        draft = {
            pointerId: nativeEvent.pointerId,
            cameraMode,
            batch: getBatch(),
            tick: getTick(),
            plane: createDraftPlane(cameraMode, startWorld),
            startScreen,
            startWorld,
            currentScreen: startScreen,
            currentWorld: startWorld
        };
        // Capture works because OrbitControls registers its listener before interactivity(),
        // as in useCuboidFaceResize.
        canvas.setPointerCapture(nativeEvent.pointerId);
        addListeners();
    }

    function getRectangle(active: Draft) {
        return getDraftRectangle(active.cameraMode, active.startWorld, active.currentWorld);
    }

    function updateDraft(event: PointerEvent): void {
        if (!draft) return;
        draft.currentScreen = { x: event.clientX, y: event.clientY };
        if (!isDrag(draft.startScreen, draft.currentScreen)) {
            previewBox = null;
            return;
        }
        const hit = raycastPlane(event, draft.plane);
        if (!hit) return;
        draft.currentWorld = [hit.x, hit.y, hit.z];
        previewBox = getDraftBox(getRectangle(draft));
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

    function getPlacement(active: Draft): CuboidPlacement | null {
        if (!isDrag(active.startScreen, active.currentScreen)) {
            return { kind: 'drop', position: active.startWorld };
        }
        // A drag whose rays never hit the plane has no rectangle to create.
        if (active.cameraMode === 'perspective' || !previewBox) return null;
        const rectangle = getRectangle(active);
        return {
            kind: 'box',
            box: getDraftBox(rectangle, fitMissingAxis(rectangle, active.batch))
        };
    }

    function onPointerMove(event: PointerEvent): void {
        if (event.pointerId === draft?.pointerId) updateDraft(event);
    }

    function onPointerUp(event: PointerEvent): void {
        if (!draft || event.pointerId !== draft.pointerId) return;
        updateDraft(event);
        const placement = getPlacement(draft);
        discardDraft();
        if (placement) onCreate(placement);
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
        if (event.type === 'pointermove') onPointerMove(pointerEvent);
        else if (event.type === 'pointerup') onPointerUp(pointerEvent);
        // A cancel or a capture loss of a different pointer must not end this draft.
        else if (pointerEvent.pointerId === draft?.pointerId) discardDraft();
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

function createDraftPlane(cameraMode: CameraMode, startWorld: Vector3): Plane {
    const normal = new ThreeVector3();
    normal.setComponent(getMissingAxis(cameraMode), 1);
    return new Plane().setFromNormalAndCoplanarPoint(normal, new ThreeVector3(...startWorld));
}
