import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { listenToSceneNavigation } from '../../PointCloudViewer/sceneNavigation';
import { createSceneNavigationInput } from './sceneNavigationInput';

describe('scene navigation input', () => {
    let input: ReturnType<typeof createSceneNavigationInput>;
    let events: ReturnType<typeof vi.fn>;
    let cleanup: () => void;
    let unsubscribe: () => void;
    beforeEach(() => {
        vi.useFakeTimers();
        input = createSceneNavigationInput();
        events = vi.fn();
        unsubscribe = listenToSceneNavigation(events);
        cleanup = input.mount();
    });
    afterEach(() => {
        cleanup();
        unsubscribe();
        vi.useRealTimers();
    });

    it('filters repeated keydown and releases keys on blur', () => {
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'W' }));
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'w', repeat: true }));
        expect(events).toHaveBeenCalledTimes(1);
        expect(events).toHaveBeenLastCalledWith({ action: 'forward', phase: 'start' });
        window.dispatchEvent(new Event('blur'));
        expect(events).toHaveBeenLastCalledWith({ action: 'forward', phase: 'stop' });
    });

    it('releases keys on keyup and ignores unrelated keys', () => {
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'q' }));
        window.dispatchEvent(new KeyboardEvent('keyup', { key: 'q' }));
        window.dispatchEvent(new KeyboardEvent('keyup', { key: 'q' }));
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'z' }));
        expect(events.mock.calls).toEqual([
            [{ action: 'rotate-left', phase: 'start' }],
            [{ action: 'rotate-left', phase: 'stop' }]
        ]);
    });

    it('ignores shortcuts and editable targets', () => {
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'w', ctrlKey: true }));
        const field = document.createElement('input');
        document.body.append(field);
        field.dispatchEvent(new KeyboardEvent('keydown', { key: 'w', bubbles: true }));
        field.remove();
        expect(events).not.toHaveBeenCalled();
    });

    it('dispatches short clicks but suppresses the click after a long hold', () => {
        input.startHold('forward');
        input.stopHold();
        input.click('forward');
        expect(events).toHaveBeenLastCalledWith({ action: 'forward', phase: 'step' });
        events.mockClear();
        input.startHold('forward');
        vi.advanceTimersByTime(180);
        input.stopHold();
        input.click('forward');
        expect(events.mock.calls).toEqual([
            [{ action: 'forward', phase: 'start' }],
            [{ action: 'forward', phase: 'stop' }]
        ]);
    });

    it('stops a pointer hold on cleanup and removes keyboard listeners', () => {
        input.startHold('left');
        vi.advanceTimersByTime(180);
        cleanup();
        expect(events).toHaveBeenLastCalledWith({ action: 'left', phase: 'stop' });
        events.mockClear();
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'w' }));
        expect(events).not.toHaveBeenCalled();
    });
});
