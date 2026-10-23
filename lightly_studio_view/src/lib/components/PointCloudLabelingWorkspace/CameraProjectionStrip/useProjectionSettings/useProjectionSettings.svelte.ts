import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { DEFAULT_PROJECTION_SETTINGS, type ProjectionSettings } from '../projectionSettings';

const PROJECTION_COLOR_MODES = new Set<ProjectionSettings['colorMode']>([
    'height',
    'intensity',
    'distance',
    'density',
    'height-distance',
    'height-density'
]);

function sanitizeProjectionSettings(value: unknown): ProjectionSettings {
    const candidate: Record<string, unknown> =
        typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};

    const numberInRange = (
        candidateValue: unknown,
        min: number,
        max: number,
        fallback: number
    ): number =>
        typeof candidateValue === 'number' && Number.isFinite(candidateValue)
            ? Math.min(max, Math.max(min, candidateValue))
            : fallback;

    return {
        pointSize: numberInRange(candidate.pointSize, 1, 10, DEFAULT_PROJECTION_SETTINGS.pointSize),
        pointOpacity: numberInRange(
            candidate.pointOpacity,
            0.1,
            1,
            DEFAULT_PROJECTION_SETTINGS.pointOpacity
        ),
        colorMode:
            typeof candidate.colorMode === 'string' &&
            PROJECTION_COLOR_MODES.has(candidate.colorMode as ProjectionSettings['colorMode'])
                ? (candidate.colorMode as ProjectionSettings['colorMode'])
                : DEFAULT_PROJECTION_SETTINGS.colorMode,
        showPoints:
            typeof candidate.showPoints === 'boolean'
                ? candidate.showPoints
                : DEFAULT_PROJECTION_SETTINGS.showPoints,
        showAnnotations:
            typeof candidate.showAnnotations === 'boolean'
                ? candidate.showAnnotations
                : DEFAULT_PROJECTION_SETTINGS.showAnnotations
    };
}

export function useProjectionSettings() {
    const settings = useSessionStorage<ProjectionSettings>(
        'lightlyStudio_cameraProjectionSettings',
        DEFAULT_PROJECTION_SETTINGS
    );

    settings.update(sanitizeProjectionSettings);

    return settings;
}
