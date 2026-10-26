import {
    navigateScene,
    startSceneNavigation,
    stopSceneNavigation,
    type SceneNavigationAction
} from '$lib/components/PointCloudViewer';

/** Active viewport checks and visual feedback used by navigation input handlers. */
interface Params {
    /** Identifies the viewport receiving navigation commands. */
    navigationId?: symbol;
    /** Enables perspective camera rotation actions. */
    allowRotation?: () => boolean;
    /** Whether this viewport currently owns navigation input. */
    isActive?: () => boolean;
    /** Reports navigation steps and held-action transitions for visual feedback. */
    onAction?: (action: SceneNavigationAction, phase: 'step' | 'start' | 'stop') => void;
}

export function createSceneNavigationInput({
    isActive = () => true,
    onAction,
    navigationId,
    allowRotation = () => true
}: Params = {}) {
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
        if (!isActive()) return;
        stopHold();
        holdRepeated = false;
        holdDelay = setTimeout(() => {
            if (!isActive()) return;
            holdRepeated = true;
            holdAction = action;
            onAction?.(action, 'start');
            startSceneNavigation(action, navigationId);
        }, 180);
    }

    function stopHold() {
        if (holdDelay) clearTimeout(holdDelay);
        if (holdAction) {
            onAction?.(holdAction, 'stop');
            stopSceneNavigation(holdAction, navigationId);
        }
        holdDelay = undefined;
        holdAction = undefined;
    }

    function cancel() {
        stopHold();
        for (const key of pressedKeys) {
            const action = keyActions[key];
            onAction?.(action, 'stop');
            stopSceneNavigation(action, navigationId);
        }
        pressedKeys.clear();
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
            if (!allowRotation() && (action === 'rotate-left' || action === 'rotate-right')) return;
            if (!isActive()) return;
            pressedKeys.add(key);
            event.preventDefault();
            onAction?.(action, 'start');
            startSceneNavigation(action, navigationId);
        };
        const handleKeyup = (event: KeyboardEvent) => {
            const key = event.key.toLowerCase();
            const action = keyActions[key];
            if (!action || !pressedKeys.has(key)) return;
            pressedKeys.delete(key);
            onAction?.(action, 'stop');
            stopSceneNavigation(action, navigationId);
        };
        window.addEventListener('keydown', handleKeydown);
        window.addEventListener('keyup', handleKeyup);
        window.addEventListener('blur', cancel);
        return () => {
            window.removeEventListener('keydown', handleKeydown);
            window.removeEventListener('keyup', handleKeyup);
            window.removeEventListener('blur', cancel);
            cancel();
        };
    }
    function click(action: SceneNavigationAction) {
        if (!isActive()) return;
        if (holdRepeated) {
            holdRepeated = false;
            return;
        }
        onAction?.(action, 'step');
        navigateScene(action, navigationId);
    }
    return { startHold, stopHold, click, mount, cancel };
}
