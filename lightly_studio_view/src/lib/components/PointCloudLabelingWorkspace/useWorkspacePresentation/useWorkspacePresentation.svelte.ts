import { fromStore } from 'svelte/store';
import type { ColorMode } from '$lib/components/PointCloudViewer';
import { useGlobalStorage } from '$lib/hooks';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

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
    const orthographic = fromStore(showOrthographicViews);
    const editing = fromStore(isEditingMode);
    const points = fromStore(pointSize);
    const helpers = fromStore(showNavigationHelpers);
    const showAnnotationTooltips = useSessionStorage<boolean>(
        'lightlyStudio_pointCloudShowAnnotationTooltips',
        true
    );
    const tooltips = fromStore(showAnnotationTooltips);

    return {
        get isEditingMode() {
            return editing.current;
        },
        get showOrthographicViews() {
            return orthographic.current;
        },
        get pointSize() {
            return points.current;
        },
        get showNavigationHelpers() {
            return helpers.current;
        },
        get showAnnotationTooltips() {
            return tooltips.current;
        },
        get colorMode() {
            return selectedColorMode ?? ('intensity' as const);
        },
        setColorMode: (mode: Exclude<ColorMode, 'none'>) => {
            selectedColorMode = mode;
        },
        setPointSize: pointSize.set,
        setShowNavigationHelpers: showNavigationHelpers.set,
        setShowAnnotationTooltips: showAnnotationTooltips.set,
        toggleOrthographicProjections: showOrthographicViews.set
    };
}
