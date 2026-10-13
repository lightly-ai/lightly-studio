export type SceneNavigationAction =
    | 'forward'
    | 'backward'
    | 'left'
    | 'right'
    | 'rotate-left'
    | 'rotate-right';

export interface SceneNavigationEvent {
    action: SceneNavigationAction;
    phase: 'step' | 'start' | 'stop';
}

const SCENE_NAVIGATION_EVENT = 'point-cloud-scene-navigation';

export function navigateScene(action: SceneNavigationAction): void {
    dispatchSceneNavigation({ action, phase: 'step' });
}

export function startSceneNavigation(action: SceneNavigationAction): void {
    dispatchSceneNavigation({ action, phase: 'start' });
}

export function stopSceneNavigation(action: SceneNavigationAction): void {
    dispatchSceneNavigation({ action, phase: 'stop' });
}

function dispatchSceneNavigation(detail: SceneNavigationEvent): void {
    window.dispatchEvent(new CustomEvent(SCENE_NAVIGATION_EVENT, { detail }));
}

export function listenToSceneNavigation(
    handler: (event: SceneNavigationEvent) => void
): () => void {
    const listener = (event: Event) => handler((event as CustomEvent<SceneNavigationEvent>).detail);
    window.addEventListener(SCENE_NAVIGATION_EVENT, listener);
    return () => window.removeEventListener(SCENE_NAVIGATION_EVENT, listener);
}
