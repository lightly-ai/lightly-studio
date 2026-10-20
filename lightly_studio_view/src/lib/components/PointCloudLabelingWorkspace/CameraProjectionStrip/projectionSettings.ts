export type ProjectionColorMode = 'single' | 'depth' | 'height' | 'intensity' | 'rgb';

export interface ProjectionSettings {
    pointSize: number;
    pointOpacity: number;
    colorMode: ProjectionColorMode;
    pointColor: string;
    showPoints: boolean;
    showAnnotations: boolean;
}

export const DEFAULT_PROJECTION_SETTINGS: ProjectionSettings = {
    pointSize: 4,
    pointOpacity: 0.95,
    colorMode: 'depth',
    pointColor: '#22d3ee',
    showPoints: true,
    showAnnotations: true
};
