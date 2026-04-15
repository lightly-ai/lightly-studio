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

Object.defineProperty(Element.prototype, 'animate', {
    writable: true,
    value: vi.fn().mockImplementation(() => {
        const animation = {
            finished: Promise.resolve(),
            cancel: vi.fn(),
            finish: vi.fn(),
            pause: vi.fn(),
            play: vi.fn(),
            reverse: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            onfinish: null as ((event: Event) => void) | null,
            oncancel: null as ((event: Event) => void) | null
        };

        queueMicrotask(() => {
            animation.onfinish?.(new Event('finish'));
        });

        return animation;
    })
});
