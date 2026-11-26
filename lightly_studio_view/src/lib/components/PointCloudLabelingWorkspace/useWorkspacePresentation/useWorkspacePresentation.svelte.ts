import { fromStore } from 'svelte/store';
import type { ColorMode } from '$lib/components/PointCloudViewer';
import { useGlobalStorage } from '$lib/hooks';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import type { PanelDock } from '../PanelDockToggle';

/** Owns scene display preferences and editing availability. */
export function useWorkspacePresentation() {
    const { isEditingMode } = useGlobalStorage();
    const showOrthographicViews = useSessionStorage<boolean>(
        'lightlyStudio_pointCloudShowOrthographicViews',
        false
    );
    let selectedColorMode = $state<Exclude<ColorMode, 'none'> | null>(null);
    const pointSize = useSessionStorage<number>('lightlyStudio_pointCloudPointSize', 2);
    const showNavigationHelpers = useSessionStorage<boolean>(
        'lightlyStudio_pointCloudShowNavigationHelpers',
        true
    );
    const orthographicDockStore = useSessionStorage<PanelDock>(
        'lightlyStudio_pointCloudOrthographicViewsDock',
        'bottom'
    );
    const orthographic = fromStore(showOrthographicViews);
    const orthographicDock = fromStore(orthographicDockStore);
    const editing = fromStore(isEditingMode);
    const points = fromStore(pointSize);
    const helpers = fromStore(showNavigationHelpers);

    return {
        get isEditingMode() {
            return editing.current;
        },
        get showOrthographicViews() {
            return orthographic.current;
        },
        get orthographicDock() {
            return orthographicDock.current;
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
        toggleOrthographicProjections: showOrthographicViews.set,
        setOrthographicDock: orthographicDockStore.set
    };
}
