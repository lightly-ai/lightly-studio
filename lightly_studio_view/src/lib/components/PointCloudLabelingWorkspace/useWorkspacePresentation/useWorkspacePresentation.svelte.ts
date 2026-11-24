import { fromStore } from 'svelte/store';
import type { ColorMode } from '$lib/components/PointCloudViewer';
import { useGlobalStorage } from '$lib/hooks';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

/** Owns scene display preferences and editing availability. */
export function useWorkspacePresentation() {
    const { isEditingMode } = useGlobalStorage();
    const orthographicViewsEnabled = useSessionStorage<boolean>(
        'lightlyStudio_pointCloudOrthographicViewsEnabled',
        true
    );
    const orthographicViewsCollapsed = useSessionStorage<boolean>(
        'lightlyStudio_pointCloudOrthographicViewsCollapsed',
        false
    );
    let selectedColorMode = $state<Exclude<ColorMode, 'none'> | null>(null);
    const pointSize = useSessionStorage<number>('lightlyStudio_pointCloudPointSize', 2);
    const showNavigationHelpers = useSessionStorage<boolean>(
        'lightlyStudio_pointCloudShowNavigationHelpers',
        true
    );
    const orthographicEnabled = fromStore(orthographicViewsEnabled);
    const orthographicCollapsed = fromStore(orthographicViewsCollapsed);
    const editing = fromStore(isEditingMode);
    const points = fromStore(pointSize);
    const helpers = fromStore(showNavigationHelpers);

    return {
        get isEditingMode() {
            return editing.current;
        },
        get orthographicViewsEnabled() {
            return orthographicEnabled.current;
        },
        get orthographicViewsCollapsed() {
            return orthographicCollapsed.current;
        },
        get pointSize() {
            return points.current;
        },
        get showNavigationHelpers() {
            return helpers.current;
        },
        get colorMode() {
            return selectedColorMode ?? ('intensity' as const);
        },
        setColorMode: (mode: Exclude<ColorMode, 'none'>) => {
            selectedColorMode = mode;
        },
        setPointSize: pointSize.set,
        setShowNavigationHelpers: showNavigationHelpers.set,
        setOrthographicViewsEnabled: orthographicViewsEnabled.set,
        setOrthographicViewsCollapsed: orthographicViewsCollapsed.set
    };
}
