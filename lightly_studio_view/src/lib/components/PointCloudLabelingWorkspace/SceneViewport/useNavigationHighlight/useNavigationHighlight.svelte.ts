import { onDestroy, onMount, untrack } from 'svelte';
import type { SceneNavigationAction } from '$lib/components/PointCloudViewer';
import { createSceneNavigationInput } from '../sceneNavigationInput';
/** Current viewport ownership and available navigation gestures. */
interface Params {
    /** Whether navigation input belongs to this viewport. */
    isActive: boolean;
    /** Routes commands to the corresponding camera. */
    navigationId?: symbol;
    /** Enables perspective camera rotation shortcuts. */
    allowRotation?: boolean;
}
/** Tracks held navigation actions and clears them when viewport ownership changes. */
export function useNavigationHighlight(getProps: () => Params) {
    let highlightedAction = $state<SceneNavigationAction | undefined>();
    let highlightTimer: ReturnType<typeof setTimeout> | undefined;
    const setHighlight = (action: SceneNavigationAction, phase: 'step' | 'start' | 'stop') => {
        highlightedAction = phase === 'stop' ? undefined : action;
        if (phase === 'step') {
            if (highlightTimer) clearTimeout(highlightTimer);
            highlightTimer = setTimeout(() => (highlightedAction = undefined), 180);
        }
    };
    const input = createSceneNavigationInput({
        isActive: () => getProps().isActive,
        navigationId: untrack(() => getProps().navigationId),
        allowRotation: () => getProps().allowRotation ?? true,
        onAction: setHighlight
    });
    onMount(input.mount);
    onDestroy(() => {
        if (highlightTimer) clearTimeout(highlightTimer);
    });
    $effect(() => {
        if (!getProps().isActive) {
            input.cancel();
            highlightedAction = undefined;
        }
    });

    return {
        input,
        get highlightedAction() {
            return highlightedAction;
        }
    };
}
