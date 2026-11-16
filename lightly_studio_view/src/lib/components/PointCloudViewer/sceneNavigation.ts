export type SceneNavigationAction =
    | 'forward'
    | 'backward'
    | 'left'
    | 'right'
    | 'rotate-left'
    | 'rotate-right';

/** Navigation command addressed to a single viewport. */
export interface SceneNavigationEvent {
    /** Identifies the viewport receiving navigation commands. */
    navigationId?: symbol;
    /** Camera movement or rotation requested by the input. */
    action: SceneNavigationAction;
    /** Whether an action is a step, starts a hold, or stops a hold. */
    phase: 'step' | 'start' | 'stop';
}

const SCENE_NAVIGATION_EVENT = 'point-cloud-scene-navigation';

export function navigateScene(action: SceneNavigationAction, navigationId?: symbol): void {
    dispatchSceneNavigation({ action, phase: 'step' }, navigationId);
}

export function startSceneNavigation(action: SceneNavigationAction, navigationId?: symbol): void {
    dispatchSceneNavigation({ action, phase: 'start' }, navigationId);
}

export function stopSceneNavigation(action: SceneNavigationAction, navigationId?: symbol): void {
    dispatchSceneNavigation({ action, phase: 'stop' }, navigationId);
}

function dispatchSceneNavigation(detail: SceneNavigationEvent, navigationId?: symbol): void {
    window.dispatchEvent(
        new CustomEvent(SCENE_NAVIGATION_EVENT, {
            detail: navigationId === undefined ? detail : { ...detail, navigationId }
        })
    );
}

export function listenToSceneNavigation(
    handler: (event: SceneNavigationEvent) => void
): () => void {
    const listener = (event: Event) => handler((event as CustomEvent<SceneNavigationEvent>).detail);
    window.addEventListener(SCENE_NAVIGATION_EVENT, listener);
    return () => window.removeEventListener(SCENE_NAVIGATION_EVENT, listener);
}
