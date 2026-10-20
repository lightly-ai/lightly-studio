import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import {
    DEFAULT_PROJECTION_SETTINGS,
    type ProjectionSettings
} from '../projectionSettings';

const PROJECTION_COLOR_MODES = new Set<ProjectionSettings['colorMode']>([
    'height',
    'intensity',
    'distance',
    'density',
    'height-distance',
    'height-density'
]);

export function useProjectionSettings() {
    const settings = useSessionStorage<ProjectionSettings>(
        'lightlyStudio_cameraProjectionSettings',
        DEFAULT_PROJECTION_SETTINGS
    );

    settings.update((value) =>
        PROJECTION_COLOR_MODES.has(value.colorMode)
            ? value
            : { ...value, colorMode: DEFAULT_PROJECTION_SETTINGS.colorMode }
    );

    return settings;
}
