import { useThrelte } from '@threlte/core';
import { onMount } from 'svelte';
import { Plane, Raycaster, Vector2, Vector3 as ThreeVector3, type Camera } from 'three';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { CameraMode, Vector3 } from '$lib/components/PointCloudLabelingWorkspace/domain';
import {
    getDraftBox,
    getDraftRectangle,
    getHeightExtent,
    getMissingAxis,
    isDrag,
    type CuboidBox,
    type CuboidPlacement,
    type DraftRectangle,
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
    plane: Plane;
    startScreen: ScreenPoint;
    startWorld: Vector3;
    currentScreen: ScreenPoint;
    currentWorld: Vector3;
    /** Footprint whose height is being set; unset while the footprint is dragged. */
    footprint?: DraftRectangle;
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

export function useCuboidDraft({ getCameraMode, getBatch, onCreate }: Params): CuboidDraftReturn {
    const { camera, renderer } = useThrelte();
    const canvas = renderer.domElement;
    const raycaster = new Raycaster();
    let draft: Draft | null = null;
    let previewBox = $state<CuboidBox | null>(null);
    /** Click that saved a height step; it also reaches the plane mesh and must not start a draft. */
    let savingClick: PointerEvent | null = null;

    function handlePlanePointerDown({ point, nativeEvent }: PlanePointerEvent): void {
        if (nativeEvent.button !== 0 || draft?.footprint || nativeEvent === savingClick) return;
        if (hasCameraModifier(nativeEvent)) return;
        discardDraft();
        const cameraMode = getCameraMode();
        const startWorld: Vector3 = [point.x, point.y, point.z];
        const startScreen = { x: nativeEvent.clientX, y: nativeEvent.clientY };
        draft = {
            pointerId: nativeEvent.pointerId,
            cameraMode,
            batch: getBatch(),
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

    function updateHeight(event: PointerEvent, footprint: DraftRectangle): void {
        const plane = createHeightPlane(footprint, camera.current);
        const hit = plane && raycastPlane(event, plane);
        if (!hit) return;
        previewBox = getDraftBox(footprint, getHeightExtent(footprint, hit.z));
    }

    function startHeightStep(active: Draft): void {
        const footprint = getRectangle(active);
        active.footprint = footprint;
        previewBox = getDraftBox(footprint, getHeightExtent(footprint, footprint.planeCoordinate));
    }

    function getPlacement(active: Draft): CuboidPlacement | null {
        if (!isDrag(active.startScreen, active.currentScreen)) {
            return { kind: 'drop', position: active.startWorld };
        }
        // A drag whose rays never hit the plane has no rectangle to create.
        if (!previewBox) return null;
        const rectangle = getRectangle(active);
        return {
            kind: 'box',
            box: getDraftBox(rectangle, fitMissingAxis(rectangle, active.batch))
        };
    }

    function onPointerMove(event: PointerEvent): void {
        if (draft?.footprint) updateHeight(event, draft.footprint);
        else if (event.pointerId === draft?.pointerId) updateDraft(event);
    }

    function onPointerUp(event: PointerEvent): void {
        if (!draft || draft.footprint || event.pointerId !== draft.pointerId) return;
        updateDraft(event);
        const hasFootprint = isDrag(draft.startScreen, draft.currentScreen) && previewBox !== null;
        if (draft.cameraMode === 'perspective' && hasFootprint) {
            startHeightStep(draft);
            return;
        }
        const placement = getPlacement(draft);
        discardDraft();
        if (placement) onCreate(placement);
    }

    function onPointerDown(event: PointerEvent): void {
        if (!draft?.footprint) return;
        if (event.button === 2) discardDraft();
        if (event.button !== 0 || hasCameraModifier(event)) return;
        const box = previewBox;
        savingClick = event;
        discardDraft();
        if (box) onCreate({ kind: 'box', box });
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
        // Releasing the footprint drag ends its pointer capture; the height step goes on.
        else if (event.type !== 'lostpointercapture' || !draft?.footprint) discardDraft();
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
        if (draft && batch !== draft.batch) discardDraft();
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
function createHeightPlane(footprint: DraftRectangle, camera: Camera): Plane | null {
    const normal = camera.getWorldDirection(new ThreeVector3()).setZ(0);
    if (normal.length() < MIN_HORIZONTAL_VIEW_LENGTH) return null;
    const centre = new ThreeVector3(...footprint.min).add(new ThreeVector3(...footprint.max));
    return new Plane().setFromNormalAndCoplanarPoint(
        normal.normalize(),
        centre.multiplyScalar(0.5)
    );
}
