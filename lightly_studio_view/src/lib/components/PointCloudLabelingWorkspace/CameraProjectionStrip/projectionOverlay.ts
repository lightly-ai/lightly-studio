import type {
    AnnotationView,
    CameraProjectionView,
    Cuboid3dAnnotationView
} from '$lib/api/lightly_studio_local/types.gen';
import type { PointBatch } from '$lib/components/PointCloudViewer/types';
import {
    DEFAULT_PROJECTION_SETTINGS,
    type ProjectionColorMode,
    type ProjectionSettings
} from './projectionSettings';

export interface ProjectedPoint {
    x: number;
    y: number;
}

export interface ProjectedPointData extends ProjectedPoint {
    depth: number;
    height: number;
    intensity: number;
    distance: number;
    density: number;
    rgb?: readonly [number, number, number];
}

export interface ProjectedSegment {
    start: ProjectedPoint;
    end: ProjectedPoint;
}

type CameraPoint = readonly [x: number, y: number, z: number];
type ColorMetric = 'depth' | 'height' | 'intensity' | 'distance' | 'density';

const NEAR_PLANE = 1e-6;

const CUBOID_EDGES = [
    [0, 1],
    [1, 3],
    [3, 2],
    [2, 0],
    [4, 5],
    [5, 7],
    [7, 6],
    [6, 4],
    [0, 4],
    [1, 5],
    [2, 6],
    [3, 7]
] as const;

export function drawProjectionOverlay(
    context: CanvasRenderingContext2D,
    projection: CameraProjectionView,
    batch: PointBatch | undefined,
    annotations: readonly AnnotationView[],
    settings: ProjectionSettings = DEFAULT_PROJECTION_SETTINGS
): void {
    context.clearRect(0, 0, projection.width, projection.height);
    if (batch && settings.showPoints) {
        const size = settings.pointSize;
        const halfSize = size / 2;
        context.globalAlpha = settings.pointOpacity;
        const metrics = getColorMetrics(settings.colorMode);
        const points = projectPointCloudData(batch, projection, 5000, metrics.includes('density'));
        const ranges = metrics.map((metric) => {
            const values = points.map((point) => getMetricValue(point, metric));
            return [Math.min(...values), Math.max(...values)] as const;
        });
        for (const point of points) {
            context.fillStyle = 'rgba(0, 0, 0, 0.8)';
            context.fillRect(point.x - halfSize - 1, point.y - halfSize - 1, size + 2, size + 2);
            context.fillStyle = getPointColor(normalizePoint(point, metrics, ranges));
            context.fillRect(point.x - halfSize, point.y - halfSize, size, size);
        }
    }
    if (settings.showAnnotations) {
        context.globalAlpha = 1;
        context.strokeStyle = '#ff5c5c';
        context.lineWidth = 2;
        context.beginPath();
        for (const segment of projectAnnotations(annotations, projection)) {
            context.moveTo(segment.start.x, segment.start.y);
            context.lineTo(segment.end.x, segment.end.y);
        }
        context.stroke();
    }
}

function getColorMetrics(mode: ProjectionColorMode): ColorMetric[] {
    if (mode === 'height-distance') return ['height', 'distance'];
    if (mode === 'height-density') return ['height', 'density'];
    if (mode === 'height') return ['height'];
    if (mode === 'intensity') return ['intensity'];
    if (mode === 'distance') return ['distance'];
    if (mode === 'density') return ['density'];
    return ['depth'];
}

function getMetricValue(point: ProjectedPointData, metric: ColorMetric): number {
    return point[metric];
}

function normalizePoint(
    point: ProjectedPointData,
    metrics: ColorMetric[],
    ranges: readonly (readonly [number, number])[]
): number {
    return (
        metrics.reduce(
            (sum, metric, index) =>
                sum + normalize(getMetricValue(point, metric), ...ranges[index]),
            0
        ) / metrics.length
    );
}

function normalize(value: number, min: number, max: number): number {
    return max === min ? 0.5 : Math.max(0, Math.min(1, (value - min) / (max - min)));
}

function getPointColor(normalizedValue: number): string {
    const hue = 230 - normalizedValue * 230;
    return `hsl(${hue} 90% 55%)`;
}

export function projectPoint(
    point: readonly [number, number, number],
    projection: CameraProjectionView
): ProjectedPoint | null {
    return projectCameraPoint(toCameraPoint(point, projection), projection);
}

function toCameraPoint(
    point: readonly [number, number, number],
    projection: CameraProjectionView
): CameraPoint {
    const matrix = projection.scene_to_camera;
    return [
        matrix[0] * point[0] + matrix[1] * point[1] + matrix[2] * point[2] + matrix[3],
        matrix[4] * point[0] + matrix[5] * point[1] + matrix[6] * point[2] + matrix[7],
        matrix[8] * point[0] + matrix[9] * point[1] + matrix[10] * point[2] + matrix[11]
    ];
}

function projectCameraPoint(
    [cameraX, cameraY, cameraZ]: CameraPoint,
    projection: CameraProjectionView
): ProjectedPoint | null {
    if (cameraZ <= NEAR_PLANE) return null;

    const k = projection.camera_matrix;
    return {
        x: (k[0] * cameraX + k[1] * cameraY + k[2] * cameraZ) / cameraZ,
        y: (k[3] * cameraX + k[4] * cameraY + k[5] * cameraZ) / cameraZ
    };
}

export function projectPointCloud(
    batch: PointBatch,
    projection: CameraProjectionView,
    maxPoints = 5000
): ProjectedPoint[] {
    const step = Math.max(1, Math.ceil(batch.count / maxPoints));
    const points: ProjectedPoint[] = [];
    for (let index = 0; index < batch.count; index += step) {
        const point = projectPoint(
            [
                batch.positions[index * 3],
                batch.positions[index * 3 + 1],
                batch.positions[index * 3 + 2]
            ],
            projection
        );
        if (
            point &&
            point.x >= 0 &&
            point.x <= projection.width &&
            point.y >= 0 &&
            point.y <= projection.height
        ) {
            points.push(point);
        }
    }
    return points;
}

/** Projects points and retains values used by camera-overlay color modes. */
export function projectPointCloudData(
    batch: PointBatch,
    projection: CameraProjectionView,
    maxPoints = 5000,
    includeDensity = false
): ProjectedPointData[] {
    const step = Math.max(1, Math.ceil(batch.count / maxPoints));
    const densityByCell = includeDensity ? getDensityByCell(batch) : undefined;
    const points: ProjectedPointData[] = [];
    for (let index = 0; index < batch.count; index += step) {
        const offset = index * 3;
        const position: [number, number, number] = [
            batch.positions[offset],
            batch.positions[offset + 1],
            batch.positions[offset + 2]
        ];
        const cameraPoint = toCameraPoint(position, projection);
        const point = projectCameraPoint(cameraPoint, projection);
        if (
            point &&
            point.x >= 0 &&
            point.x <= projection.width &&
            point.y >= 0 &&
            point.y <= projection.height
        ) {
            points.push({
                ...point,
                depth: cameraPoint[2],
                height: position[2],
                intensity: batch.intensities[index],
                distance: Math.hypot(...position),
                density: densityByCell
                    ? Math.log1p(densityByCell.get(getCellKey(position)) ?? 1)
                    : 0,
                rgb: batch.colors
                    ? [batch.colors[offset], batch.colors[offset + 1], batch.colors[offset + 2]]
                    : undefined
            });
        }
    }
    return points;
}

function getDensityByCell(batch: PointBatch): Map<string, number> {
    const counts = new Map<string, number>();
    for (let index = 0; index < batch.count; index++) {
        const offset = index * 3;
        const position: [number, number, number] = [
            batch.positions[offset],
            batch.positions[offset + 1],
            batch.positions[offset + 2]
        ];
        const key = getCellKey(position);
        counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return counts;
}

function getCellKey(position: readonly [number, number, number]): string {
    const cellSize = 0.5;
    return position.map((coordinate) => Math.floor(coordinate / cellSize)).join(',');
}

export function projectCuboid(
    cuboid: Cuboid3dAnnotationView,
    projection: CameraProjectionView
): ProjectedSegment[] {
    const corners = cuboidCorners(cuboid).map((corner) => toCameraPoint(corner, projection));
    return CUBOID_EDGES.flatMap(([startIndex, endIndex]) => {
        const clipped3d = clipToNearPlane(corners[startIndex], corners[endIndex]);
        if (!clipped3d) return [];
        const start = projectCameraPoint(clipped3d[0], projection);
        const end = projectCameraPoint(clipped3d[1], projection);
        if (!start || !end) return [];
        const clipped2d = clipToImage(start, end, projection);
        return clipped2d ? [clipped2d] : [];
    });
}

function clipToNearPlane(start: CameraPoint, end: CameraPoint): [CameraPoint, CameraPoint] | null {
    const startInside = start[2] > NEAR_PLANE;
    const endInside = end[2] > NEAR_PLANE;
    if (!startInside && !endInside) return null;
    if (startInside && endInside) return [start, end];

    const t = (NEAR_PLANE - start[2]) / (end[2] - start[2]);
    const intersection: CameraPoint = [
        start[0] + t * (end[0] - start[0]),
        start[1] + t * (end[1] - start[1]),
        NEAR_PLANE
    ];
    return startInside ? [start, intersection] : [intersection, end];
}

/** Clips a projected cuboid edge to the camera image rectangle. */
function clipToImage(
    start: ProjectedPoint,
    end: ProjectedPoint,
    projection: CameraProjectionView
): ProjectedSegment | null {
    let t0 = 0;
    let t1 = 1;
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const boundaries: Array<[number, number]> = [
        [-dx, start.x],
        [dx, projection.width - start.x],
        [-dy, start.y],
        [dy, projection.height - start.y]
    ];

    for (const [p, q] of boundaries) {
        if (p === 0) {
            if (q < 0) return null;
            continue;
        }
        const ratio = q / p;
        if (p < 0) t0 = Math.max(t0, ratio);
        else t1 = Math.min(t1, ratio);
        if (t0 > t1) return null;
    }

    return {
        start: { x: start.x + t0 * dx, y: start.y + t0 * dy },
        end: { x: start.x + t1 * dx, y: start.y + t1 * dy }
    };
}

export function projectAnnotations(
    annotations: readonly AnnotationView[],
    projection: CameraProjectionView
): ProjectedSegment[] {
    return annotations.flatMap((annotation) =>
        annotation.cuboid_3d_details ? projectCuboid(annotation.cuboid_3d_details, projection) : []
    );
}

function cuboidCorners(cuboid: Cuboid3dAnnotationView): Array<[number, number, number]> {
    const half = [cuboid.sx / 2, cuboid.sy / 2, cuboid.sz / 2] as const;
    const quaternion = [cuboid.qx, cuboid.qy, cuboid.qz, cuboid.qw] as const;
    return [
        [-1, -1, -1],
        [-1, -1, 1],
        [-1, 1, -1],
        [-1, 1, 1],
        [1, -1, -1],
        [1, -1, 1],
        [1, 1, -1],
        [1, 1, 1]
    ].map(([x, y, z]) => {
        const rotated = rotateVector([x * half[0], y * half[1], z * half[2]], quaternion);
        return [rotated[0] + cuboid.px, rotated[1] + cuboid.py, rotated[2] + cuboid.pz];
    });
}

function rotateVector(
    vector: readonly [number, number, number],
    quaternion: readonly [number, number, number, number]
): [number, number, number] {
    const [x, y, z, w] = quaternion;
    const [vx, vy, vz] = vector;
    const tx = 2 * (y * vz - z * vy);
    const ty = 2 * (z * vx - x * vz);
    const tz = 2 * (x * vy - y * vx);
    return [
        vx + w * tx + y * tz - z * ty,
        vy + w * ty + z * tx - x * tz,
        vz + w * tz + x * ty - y * tx
    ];
}
