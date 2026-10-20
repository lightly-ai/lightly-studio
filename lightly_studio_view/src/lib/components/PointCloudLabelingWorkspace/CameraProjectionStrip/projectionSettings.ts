import type { ColorMode } from '$lib/components/PointCloudViewer';

export type ProjectionColorMode = Exclude<ColorMode, 'none' | 'rgb'>;

export type ProjectionSettings = {
    pointSize: number;
    pointOpacity: number;
    colorMode: ProjectionColorMode;
    showPoints: boolean;
    showAnnotations: boolean;
};

export const DEFAULT_PROJECTION_SETTINGS: ProjectionSettings = {
    pointSize: 4,
    pointOpacity: 0.95,
    colorMode: 'intensity',
    showPoints: true,
    showAnnotations: true
};
