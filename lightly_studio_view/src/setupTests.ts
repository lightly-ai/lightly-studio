import '@testing-library/jest-dom';
import { vi } from 'vitest';

Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn()
    }))
});

vi.mock('$env/static/public', () => ({
    PUBLIC_SAMPLES_URL: 'http://mock-url.com',
    PUBLIC_LIGHTLY_STUDIO_API_URL: 'http://mock-url.com/api'
}));

// jsdom has no ResizeObserver. Track instances so tests can trigger the callback manually
// (jsdom reports scrollWidth/clientWidth as 0, so observers never fire on their own).
class MockResizeObserver implements ResizeObserver {
    static instances: MockResizeObserver[] = [];
    private readonly callback: ResizeObserverCallback;

    constructor(callback: ResizeObserverCallback) {
        this.callback = callback;
        MockResizeObserver.instances.push(this);
    }

    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}

    trigger(): void {
        this.callback([], this);
    }
}

vi.stubGlobal('ResizeObserver', MockResizeObserver);

// jsdom does not implement scrollIntoView, which bits-ui Command/Select call when
// navigating items. Provide a no-op so those components can render in tests.
Object.defineProperty(Element.prototype, 'scrollIntoView', {
    writable: true,
    value: vi.fn()
});

Object.defineProperty(Element.prototype, 'animate', {
    writable: true,
    // Use a plain function (not vi.fn()) so vi.restoreAllMocks() cannot clear the
    // implementation. If vi.fn() were used, afterEach(vi.restoreAllMocks) would reset it,
    // causing microtask-queued onfinish callbacks to call element.animate() and get
    // undefined back, then crash when Svelte sets animation.onfinish on the result.
    value: function () {
        const animation: {
            finished: Promise<void>;
            cancel: () => void;
            finish: () => void;
            pause: () => void;
            play: () => void;
            reverse: () => void;
            addEventListener: () => void;
            removeEventListener: () => void;
            onfinish: ((event: Event) => void) | null;
            oncancel: ((event: Event) => void) | null;
            effect: unknown;
        } = {
            finished: Promise.resolve(),
            cancel: () => {},
            finish: () => {},
            pause: () => {},
            play: () => {},
            reverse: () => {},
            addEventListener: () => {},
            removeEventListener: () => {},
            onfinish: null,
            oncancel: null,
            effect: null
        };

        queueMicrotask(() => {
            animation.onfinish?.(new Event('finish'));
        });

        return animation;
    }
});
