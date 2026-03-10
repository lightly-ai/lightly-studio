import { isTextInputTarget } from '$lib/utils';

const MOVEMENT_KEY_CODES = new Set(['KeyW', 'KeyA', 'KeyS', 'KeyD']);
const KEYBOARD_PAN_SPEED_PX_PER_SECOND = 600;
const MOVEMENT_KEY_CODES_BY_KEY = new Map([
    ['w', 'KeyW'],
    ['a', 'KeyA'],
    ['s', 'KeyS'],
    ['d', 'KeyD']
]);

type UseKeyboardPanArgs = {
    getContainerElement: () => SVGSVGElement | null;
    isPanEnabled: () => boolean;
    isZoomEnabled: () => boolean;
    panByPixels: (x: number, y: number) => boolean;
};

type KeyboardPanDirection = {
    x: number;
    y: number;
};

export const useKeyboardPan = ({
    getContainerElement,
    isPanEnabled,
    isZoomEnabled,
    panByPixels
}: UseKeyboardPanArgs) => {
    const pressedMovementKeys = new Set<string>();
    let isSpacePanActive = false;
    let isKeyboardPanContextActive = false;
    let keyboardPanAnimationFrameId: number | null = null;

    const stopKeyboardPanLoop = () => {
        if (keyboardPanAnimationFrameId === null) return;

        cancelAnimationFrame(keyboardPanAnimationFrameId);
        keyboardPanAnimationFrameId = null;
    };

    const resetKeyboardPanState = () => {
        pressedMovementKeys.clear();
        isSpacePanActive = false;
        stopKeyboardPanLoop();
    };

    const isSpaceKey = (event: KeyboardEvent) =>
        event.code === 'Space' ||
        event.key === ' ' ||
        event.key === 'Space' ||
        event.key === 'Spacebar';

    const getMovementCode = (event: KeyboardEvent) => {
        if (MOVEMENT_KEY_CODES.has(event.code)) {
            return event.code;
        }

        return MOVEMENT_KEY_CODES_BY_KEY.get(event.key.toLowerCase());
    };

    const getKeyboardPanDirection = (): KeyboardPanDirection => {
        let x = 0;
        let y = 0;

        // W/A/S/D move the viewport like game controls.
        if (pressedMovementKeys.has('KeyW')) y += 1;
        if (pressedMovementKeys.has('KeyS')) y -= 1;
        if (pressedMovementKeys.has('KeyA')) x += 1;
        if (pressedMovementKeys.has('KeyD')) x -= 1;

        if (x !== 0 && y !== 0) {
            x *= Math.SQRT1_2;
            y *= Math.SQRT1_2;
        }

        return { x, y };
    };

    const panWithKeyboard = (elapsedSeconds: number) => {
        const direction = getKeyboardPanDirection();
        if (direction.x === 0 && direction.y === 0) {
            return false;
        }

        const panDistance = KEYBOARD_PAN_SPEED_PX_PER_SECOND * elapsedSeconds;
        return panByPixels(direction.x * panDistance, direction.y * panDistance);
    };

    const ensureKeyboardPanLoop = () => {
        if (keyboardPanAnimationFrameId !== null) return;
        let previousFrameTimestamp: number | null = null;

        const onKeyboardPanFrame = (timestamp: number) => {
            if (
                !getContainerElement() ||
                !isPanEnabled() ||
                !isZoomEnabled() ||
                !isSpacePanActive ||
                pressedMovementKeys.size === 0
            ) {
                stopKeyboardPanLoop();
                return;
            }

            const elapsedSeconds =
                previousFrameTimestamp === null
                    ? 1 / 60
                    : (timestamp - previousFrameTimestamp) / 1000;
            previousFrameTimestamp = timestamp;

            const didPan = panWithKeyboard(elapsedSeconds);
            if (!didPan) {
                stopKeyboardPanLoop();
                return;
            }

            keyboardPanAnimationFrameId = requestAnimationFrame(onKeyboardPanFrame);
        };

        keyboardPanAnimationFrameId = requestAnimationFrame(onKeyboardPanFrame);
    };

    const handleWindowKeyDown = (event: KeyboardEvent) => {
        if (!isKeyboardPanContextActive) return;
        if (!isPanEnabled() || !isZoomEnabled()) return;
        if (isTextInputTarget(event.target)) return;

        if (isSpaceKey(event)) {
            isSpacePanActive = true;
            event.preventDefault();
            if (pressedMovementKeys.size > 0) {
                panWithKeyboard(1 / 60);
                ensureKeyboardPanLoop();
            }
            return;
        }

        const movementCode = getMovementCode(event);
        if (!movementCode) return;

        pressedMovementKeys.add(movementCode);
        if (!isSpacePanActive) return;

        event.preventDefault();
        panWithKeyboard(1 / 60);
        ensureKeyboardPanLoop();
    };

    const handleWindowKeyUp = (event: KeyboardEvent) => {
        if (isSpaceKey(event)) {
            isSpacePanActive = false;
            stopKeyboardPanLoop();
            return;
        }

        const movementCode = getMovementCode(event);
        if (!movementCode) return;

        pressedMovementKeys.delete(movementCode);

        if (pressedMovementKeys.size === 0) {
            stopKeyboardPanLoop();
        }
    };

    const handleContainerMouseEnter = () => {
        isKeyboardPanContextActive = true;
    };

    const handleContainerMouseLeave = () => {
        isKeyboardPanContextActive = false;
        resetKeyboardPanState();
    };

    const handleWindowMouseDown = (event: MouseEvent) => {
        if (!(event.target instanceof Node)) return;
        if (getContainerElement()?.contains(event.target)) {
            isKeyboardPanContextActive = true;
            return;
        }

        isKeyboardPanContextActive = false;
        resetKeyboardPanState();
    };

    const handleWindowBlur = () => {
        resetKeyboardPanState();
        isKeyboardPanContextActive = false;
    };

    const cleanup = () => {
        resetKeyboardPanState();
        isKeyboardPanContextActive = false;
    };

    return {
        handleContainerMouseEnter,
        handleContainerMouseLeave,
        handleWindowKeyDown,
        handleWindowKeyUp,
        handleWindowMouseDown,
        handleWindowBlur,
        cleanup
    };
};
