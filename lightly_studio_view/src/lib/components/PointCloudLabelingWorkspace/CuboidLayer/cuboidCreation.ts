import * as THREE from 'three';
import type {
    Bounds3,
    CoordinateFrame,
    CuboidAnnotation,
    Vector3,
    WorkspaceTool
} from '$lib/components/PointCloudLabelingWorkspace/domain';

/** Default cuboid size placed on creation: x × y × z in metres. */
export const DEFAULT_CUBOID_SIZE: [number, number, number] = [4.5, 1.8, 1.5];

/** Configuration required to create cuboids in the active point-cloud frame. */
export interface CuboidCreationConfig {
    annotationClassId: string;
    frameId: string;
    coordinateFrame: CoordinateFrame;
    annotationSourceId: string;
    oncreate: (cuboid: Omit<CuboidAnnotation, 'id'>) => void;
}

interface RaycastContext {
    camera: THREE.Camera;
    scene: THREE.Scene;
    renderer: THREE.WebGLRenderer;
}

interface CuboidCreationListenerParams {
    canvas: HTMLCanvasElement;
    activeTool: WorkspaceTool;
    getContext: () => RaycastContext;
    config: CuboidCreationConfig;
    pointCloudBounds: Bounds3;
}

const PICK_RADIUS_PX = 4;

export function computePointsThreshold(
    cameraFov: number,
    elementHeight: number,
    depth: number,
    pickRadiusPx = PICK_RADIUS_PX
): number {
    if (elementHeight <= 0 || depth <= 0) return 0;
    const visibleWorldHeight = 2 * depth * Math.tan((cameraFov * Math.PI) / 360);
    return (visibleWorldHeight / elementHeight) * pickRadiusPx;
}

export function clampToBounds(center: Vector3, bounds: Bounds3): Vector3 {
    return [
        Math.max(bounds.min[0], Math.min(bounds.max[0], center[0])),
        Math.max(bounds.min[1], Math.min(bounds.max[1], center[1])),
        Math.max(bounds.min[2], Math.min(bounds.max[2], center[2]))
    ];
}

function getPointCloudDepth(camera: THREE.PerspectiveCamera, bounds: Bounds3): number {
    const [minX, minY, minZ] = bounds.min;
    const [maxX, maxY, maxZ] = bounds.max;
    const center = new THREE.Vector3((minX + maxX) / 2, (minY + maxY) / 2, (minZ + maxZ) / 2);
    const diagonal = new THREE.Vector3(maxX - minX, maxY - minY, maxZ - minZ).length() / 2;
    return Math.max(camera.near, camera.position.distanceTo(center) + diagonal);
}

function createRaycaster(
    camera: THREE.Camera,
    elementHeight: number,
    bounds: Bounds3
): THREE.Raycaster {
    const raycaster = new THREE.Raycaster();
    if (camera instanceof THREE.PerspectiveCamera) {
        raycaster.params.Points = {
            threshold: computePointsThreshold(
                camera.fov,
                elementHeight,
                getPointCloudDepth(camera, bounds)
            )
        };
    }
    return raycaster;
}

function getPointerPosition(
    event: MouseEvent,
    element: HTMLCanvasElement
): THREE.Vector2 | undefined {
    const rect = element.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    return new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1
    );
}

function getPoints(scene: THREE.Scene): THREE.Points[] {
    const points: THREE.Points[] = [];
    scene.traverse((object) => {
        if (object.type === 'Points') points.push(object as THREE.Points);
    });
    return points;
}

function raycastPoint(
    event: MouseEvent,
    context: RaycastContext,
    bounds: Bounds3
): THREE.Vector3 | undefined {
    const pointer = getPointerPosition(event, context.renderer.domElement);
    if (!pointer) return;
    const raycaster = createRaycaster(
        context.camera,
        context.renderer.domElement.clientHeight,
        bounds
    );
    raycaster.setFromCamera(pointer, context.camera);
    const points = getPoints(context.scene);
    points.forEach((pointCloud) => pointCloud.updateWorldMatrix(true, false));
    return raycaster.intersectObjects(points, false)[0]?.point;
}

function createCuboid(center: Vector3, config: CuboidCreationConfig): Omit<CuboidAnnotation, 'id'> {
    return {
        frameId: config.frameId,
        coordinateFrame: config.coordinateFrame,
        annotationClassId: config.annotationClassId,
        annotationSourceId: config.annotationSourceId,
        trackId: null,
        keyframeId: null,
        center,
        size: DEFAULT_CUBOID_SIZE,
        rotation: [0, 0, 0, 1]
    };
}

export function addCuboidCreationListeners({
    canvas,
    activeTool,
    getContext,
    config,
    pointCloudBounds
}: CuboidCreationListenerParams): () => void {
    function onClick(event: MouseEvent): void {
        if (activeTool !== 'create-cuboid') return;
        const point = raycastPoint(event, getContext(), pointCloudBounds);
        if (point)
            config.oncreate(createCuboid(clampToBounds(point.toArray(), pointCloudBounds), config));
    }

    const target = canvas.parentElement ?? canvas;
    target.addEventListener('click', onClick);
    return () => target.removeEventListener('click', onClick);
}
