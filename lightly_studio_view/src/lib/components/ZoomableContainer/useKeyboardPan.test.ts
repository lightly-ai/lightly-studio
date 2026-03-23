import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useKeyboardPan } from './useKeyboardPan';

type SetupKeyboardPanOptions = {
    panEnabled?: boolean;
    zoomEnabled?: boolean;
    panByPixelsReturnValue?: boolean;
};

type ScheduledFrame = {
    id: number;
    callback: FrameRequestCallback;
};

let nextFrameId = 1;
let scheduledFrames: ScheduledFrame[] = [];

const runNextAnimationFrame = (timestamp = 16) => {
    const scheduledFrame = scheduledFrames.shift();
    expect(scheduledFrame).toBeTruthy();
    scheduledFrame!.callback(timestamp);
};

const dispatchKeyboardEvent = (
    target: Window | HTMLElement,
    eventType: 'keydown' | 'keyup',
    init: KeyboardEventInit
) => {
    const event = new KeyboardEvent(eventType, { bubbles: true, cancelable: true, ...init });
    target.dispatchEvent(event);
    return event;
};

const setupKeyboardPan = (options: SetupKeyboardPanOptions = {}) => {
    let panEnabled = options.panEnabled ?? true;
    let zoomEnabled = options.zoomEnabled ?? true;

    const container = document.createElementNS(
        'http://www.w3.org/2000/svg',
        'svg'
    ) as SVGSVGElement;
    document.body.appendChild(container);

    const panByPixels = vi.fn<(x: number, y: number) => boolean>(
        () => options.panByPixelsReturnValue ?? true
    );

    const {
        handleContainerMouseEnter,
        handleContainerMouseLeave,
        handleWindowKeyDown,
        handleWindowKeyUp,
        handleWindowMouseDown,
        handleWindowBlur,
        cleanup
    } = useKeyboardPan({
        getContainerElement: () => container,
        isPanEnabled: () => panEnabled,
        isZoomEnabled: () => zoomEnabled,
        panByPixels
    });

    container.addEventListener('mouseenter', handleContainerMouseEnter);
    container.addEventListener('mouseleave', handleContainerMouseLeave);
    window.addEventListener('keydown', handleWindowKeyDown, { capture: true });
    window.addEventListener('keyup', handleWindowKeyUp, { capture: true });
    window.addEventListener('mousedown', handleWindowMouseDown);
    window.addEventListener('blur', handleWindowBlur);

    return {
        container,
        panByPixels,
        unmount: () => {
            cleanup();
            container.removeEventListener('mouseenter', handleContainerMouseEnter);
            container.removeEventListener('mouseleave', handleContainerMouseLeave);
            window.removeEventListener('keydown', handleWindowKeyDown, { capture: true });
            window.removeEventListener('keyup', handleWindowKeyUp, { capture: true });
            window.removeEventListener('mousedown', handleWindowMouseDown);
            window.removeEventListener('blur', handleWindowBlur);
        },
        setPanEnabled: (nextPanEnabled: boolean) => {
            panEnabled = nextPanEnabled;
        },
        setZoomEnabled: (nextZoomEnabled: boolean) => {
            zoomEnabled = nextZoomEnabled;
        }
    };
};

describe('useKeyboardPan', () => {
    beforeEach(() => {
        nextFrameId = 1;
        scheduledFrames = [];

        vi.stubGlobal(
            'requestAnimationFrame',
            vi.fn((callback: FrameRequestCallback) => {
                const id = nextFrameId++;
                scheduledFrames.push({ id, callback });
                return id;
            })
        );

        vi.stubGlobal(
            'cancelAnimationFrame',
            vi.fn((id: number) => {
                scheduledFrames = scheduledFrames.filter(
                    (scheduledFrame) => scheduledFrame.id !== id
                );
            })
        );
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        document.body.innerHTML = '';
    });

    it('does not pan before keyboard pan context is active', () => {
        const { panByPixels, unmount } = setupKeyboardPan();

        dispatchKeyboardEvent(window, 'keydown', { key: ' ', code: 'Space' });
        dispatchKeyboardEvent(window, 'keydown', { key: 'w', code: 'KeyW' });

        expect(panByPixels).not.toHaveBeenCalled();
        expect(requestAnimationFrame).not.toHaveBeenCalled();

        unmount();
    });

    it('activates keyboard pan context when mousedown happens inside the container', () => {
        const { container, panByPixels, unmount } = setupKeyboardPan();

        window.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        expect(panByPixels).not.toHaveBeenCalled();

        container.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        dispatchKeyboardEvent(window, 'keydown', { key: ' ', code: 'Space' });
        dispatchKeyboardEvent(window, 'keydown', { key: 'w', code: 'KeyW' });

        expect(panByPixels).toHaveBeenCalledTimes(1);

        unmount();
    });

    it('pans immediately and starts a loop for Space + W', () => {
        const { container, panByPixels, unmount } = setupKeyboardPan();

        container.dispatchEvent(new MouseEvent('mouseenter'));

        const spaceDownEvent = dispatchKeyboardEvent(window, 'keydown', {
            key: ' ',
            code: 'Space'
        });
        const movementDownEvent = dispatchKeyboardEvent(window, 'keydown', {
            key: 'w',
            code: 'KeyW'
        });

        expect(spaceDownEvent.defaultPrevented).toBe(true);
        expect(movementDownEvent.defaultPrevented).toBe(true);
        expect(panByPixels).toHaveBeenNthCalledWith(1, 0, 10);
        expect(scheduledFrames).toHaveLength(1);

        runNextAnimationFrame();

        expect(panByPixels).toHaveBeenNthCalledWith(2, 0, 10);

        unmount();
    });

    it('starts panning when Space is pressed after movement key is already held', () => {
        const { container, panByPixels, unmount } = setupKeyboardPan();

        container.dispatchEvent(new MouseEvent('mouseenter'));

        dispatchKeyboardEvent(window, 'keydown', { key: 'w', code: 'KeyW' });
        expect(panByPixels).not.toHaveBeenCalled();

        dispatchKeyboardEvent(window, 'keydown', { key: ' ', code: 'Space' });
        expect(panByPixels).toHaveBeenNthCalledWith(1, 0, 10);

        unmount();
    });

    it('supports keyboard pan when Space comes as event.key', () => {
        const { container, panByPixels, unmount } = setupKeyboardPan();

        container.dispatchEvent(new MouseEvent('mouseenter'));

        dispatchKeyboardEvent(window, 'keydown', { key: 'Space' });
        dispatchKeyboardEvent(window, 'keydown', { key: 'w' });

        expect(panByPixels).toHaveBeenCalledTimes(1);
        expect(panByPixels).toHaveBeenNthCalledWith(1, 0, 10);

        dispatchKeyboardEvent(window, 'keyup', { key: 'w' });
        dispatchKeyboardEvent(window, 'keyup', { key: 'Space' });

        unmount();
    });

    it('handles Space even when target listeners stop keydown propagation', () => {
        const { container, panByPixels, unmount } = setupKeyboardPan();

        const focusElement = document.createElement('button');
        focusElement.addEventListener('keydown', (event) => {
            event.stopPropagation();
        });
        container.appendChild(focusElement);

        container.dispatchEvent(new MouseEvent('mouseenter'));

        dispatchKeyboardEvent(focusElement, 'keydown', { key: 'Space' });
        dispatchKeyboardEvent(focusElement, 'keydown', { key: 'w' });

        expect(panByPixels).toHaveBeenCalledTimes(1);
        expect(panByPixels).toHaveBeenNthCalledWith(1, 0, 10);

        unmount();
    });

    it('ignores keyboard pan hotkeys from text input targets', () => {
        const { container, panByPixels, unmount } = setupKeyboardPan();
        const input = document.createElement('input');
        document.body.appendChild(input);

        container.dispatchEvent(new MouseEvent('mouseenter'));

        const spaceDownEvent = dispatchKeyboardEvent(input, 'keydown', { key: ' ', code: 'Space' });
        const movementDownEvent = dispatchKeyboardEvent(input, 'keydown', {
            key: 'w',
            code: 'KeyW'
        });

        expect(spaceDownEvent.defaultPrevented).toBe(false);
        expect(movementDownEvent.defaultPrevented).toBe(false);
        expect(panByPixels).not.toHaveBeenCalled();
        expect(requestAnimationFrame).not.toHaveBeenCalled();

        unmount();
    });

    it('normalizes diagonal movement speed', () => {
        const { container, panByPixels, unmount } = setupKeyboardPan();

        container.dispatchEvent(new MouseEvent('mouseenter'));
        dispatchKeyboardEvent(window, 'keydown', { key: ' ', code: 'Space' });
        dispatchKeyboardEvent(window, 'keydown', { key: 'w', code: 'KeyW' });
        dispatchKeyboardEvent(window, 'keydown', { key: 'd', code: 'KeyD' });

        const [panX, panY] = panByPixels.mock.lastCall!;

        expect(panX).toBeCloseTo(-10 * Math.SQRT1_2);
        expect(panY).toBeCloseTo(10 * Math.SQRT1_2);

        unmount();
    });

    it('resets keyboard pan state on mouseleave', () => {
        const { container, panByPixels, unmount } = setupKeyboardPan();

        container.dispatchEvent(new MouseEvent('mouseenter'));
        dispatchKeyboardEvent(window, 'keydown', { key: ' ', code: 'Space' });
        dispatchKeyboardEvent(window, 'keydown', { key: 'w', code: 'KeyW' });
        expect(panByPixels).toHaveBeenCalledTimes(1);
        expect(scheduledFrames).toHaveLength(1);

        container.dispatchEvent(new MouseEvent('mouseleave'));
        expect(scheduledFrames).toHaveLength(0);

        dispatchKeyboardEvent(window, 'keydown', { key: ' ', code: 'Space' });
        dispatchKeyboardEvent(window, 'keydown', { key: 'w', code: 'KeyW' });
        expect(panByPixels).toHaveBeenCalledTimes(1);

        unmount();
    });

    it('stops scheduling animation frames when panByPixels returns false', () => {
        const { container, panByPixels, unmount } = setupKeyboardPan({
            panByPixelsReturnValue: false
        });

        container.dispatchEvent(new MouseEvent('mouseenter'));
        dispatchKeyboardEvent(window, 'keydown', { key: ' ', code: 'Space' });
        dispatchKeyboardEvent(window, 'keydown', { key: 'w', code: 'KeyW' });
        expect(scheduledFrames).toHaveLength(1);

        runNextAnimationFrame();

        expect(panByPixels).toHaveBeenCalledTimes(2);
        expect(scheduledFrames).toHaveLength(0);

        unmount();
    });

    it('does not pan when pan or zoom is disabled', () => {
        const { container, panByPixels, setPanEnabled, setZoomEnabled, unmount } =
            setupKeyboardPan();

        container.dispatchEvent(new MouseEvent('mouseenter'));
        setPanEnabled(false);

        dispatchKeyboardEvent(window, 'keydown', { key: ' ', code: 'Space' });
        dispatchKeyboardEvent(window, 'keydown', { key: 'w', code: 'KeyW' });
        expect(panByPixels).not.toHaveBeenCalled();

        setPanEnabled(true);
        setZoomEnabled(false);

        dispatchKeyboardEvent(window, 'keydown', { key: ' ', code: 'Space' });
        dispatchKeyboardEvent(window, 'keydown', { key: 'w', code: 'KeyW' });
        expect(panByPixels).not.toHaveBeenCalled();

        unmount();
    });
});
