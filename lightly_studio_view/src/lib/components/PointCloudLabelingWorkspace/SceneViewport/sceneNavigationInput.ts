import {
    navigateScene,
    startSceneNavigation,
    stopSceneNavigation,
    type SceneNavigationAction
} from '$lib/components/PointCloudViewer';

export function createSceneNavigationInput() {
    const keyActions: Record<string, SceneNavigationAction> = {
        w: 'forward',
        a: 'left',
        s: 'backward',
        d: 'right',
        q: 'rotate-left',
        e: 'rotate-right'
    };
    let holdDelay: ReturnType<typeof setTimeout> | undefined;
    let holdAction: SceneNavigationAction | undefined;
    let holdRepeated = false;
    const pressedKeys = new Set<string>();

    function startHold(action: SceneNavigationAction) {
        stopHold();
        holdRepeated = false;
        holdDelay = setTimeout(() => {
            holdRepeated = true;
            holdAction = action;
            startSceneNavigation(action);
        }, 180);
    }

    function stopHold() {
        if (holdDelay) clearTimeout(holdDelay);
        if (holdAction) stopSceneNavigation(holdAction);
        holdDelay = undefined;
        holdAction = undefined;
    }

    function mount() {
        const handleKeydown = (event: KeyboardEvent) => {
            if (event.altKey || event.ctrlKey || event.metaKey) return;
            const target = event.target;
            if (
                target instanceof HTMLElement &&
                target.closest('input, textarea, select, [contenteditable="true"]')
            ) {
                return;
            }
            const key = event.key.toLowerCase();
            const action = keyActions[key];
            if (!action || pressedKeys.has(key)) return;
            pressedKeys.add(key);
            event.preventDefault();
            startSceneNavigation(action);
        };
        const handleKeyup = (event: KeyboardEvent) => {
            const key = event.key.toLowerCase();
            const action = keyActions[key];
            if (!action || !pressedKeys.has(key)) return;
            pressedKeys.delete(key);
            stopSceneNavigation(action);
        };
        const stopPressedKeys = () => {
            for (const key of pressedKeys) stopSceneNavigation(keyActions[key]);
            pressedKeys.clear();
        };
        window.addEventListener('keydown', handleKeydown);
        window.addEventListener('keyup', handleKeyup);
        window.addEventListener('blur', stopPressedKeys);
        return () => {
            window.removeEventListener('keydown', handleKeydown);
            window.removeEventListener('keyup', handleKeyup);
            window.removeEventListener('blur', stopPressedKeys);
            stopPressedKeys();
            stopHold();
        };
    }
    function click(action: SceneNavigationAction) {
        if (holdRepeated) {
            holdRepeated = false;
            return;
        }
        navigateScene(action);
    }
    return { startHold, stopHold, click, mount };
}
