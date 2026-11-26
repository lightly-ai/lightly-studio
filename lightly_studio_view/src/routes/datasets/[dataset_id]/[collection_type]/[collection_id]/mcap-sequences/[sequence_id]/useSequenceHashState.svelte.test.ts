import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { afterNavigate, goto } from '$app/navigation';
import { useSequenceHashState } from './useSequenceHashState.svelte';

const SEQUENCE_URL = 'http://localhost/datasets/d/mcap/c/mcap-sequences/s';

// Reactive so that the hook effects see URL changes; the mocks read it lazily.
const route = $state({
    url: new URL(`${SEQUENCE_URL}#tick=2`),
    navigationType: null as string | null
});

vi.mock('$app/navigation', () => ({ goto: vi.fn(), afterNavigate: vi.fn() }));
vi.mock('$app/state', () => ({
    page: {
        get url() {
            return route.url;
        },
        state: {}
    },
    navigating: {
        get type() {
            return route.navigationType;
        }
    }
}));

const disposers: (() => void)[] = [];

function setup() {
    const input = $state({ sequenceId: 'sequence-1' });
    let hashState!: ReturnType<typeof useSequenceHashState>;
    disposers.push(
        $effect.root(() => {
            hashState = useSequenceHashState({ getSequenceId: () => input.sequenceId });
        })
    );
    flushSync();
    return { input, hashState };
}

const lastGoto = () => {
    const [url, options] = vi.mocked(goto).mock.lastCall!;
    return { hash: (url as URL).hash, options };
};

// SvelteKit updates `page.url` during the navigation and calls afterNavigate at its end.
const popstate = (toUrl: string) => {
    const fromUrl = route.url;
    route.navigationType = 'popstate';
    route.url = new URL(toUrl);
    flushSync();
    const callback = vi.mocked(afterNavigate).mock.lastCall![0] as (nav: unknown) => void;
    callback({ type: 'popstate', from: { url: fromUrl }, to: { url: route.url } });
    route.navigationType = null;
    flushSync();
};

describe('useSequenceHashState', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        route.url = new URL(`${SEQUENCE_URL}#tick=2`);
        route.navigationType = null;
    });

    afterEach(() => {
        disposers.splice(0).forEach((dispose) => dispose());
        vi.restoreAllMocks();
    });

    it('reads the tick and camera from the hash', () => {
        route.url = new URL(`${SEQUENCE_URL}#tick=2&camera=CAM_B`);
        const { hashState } = setup();

        expect(hashState.tick).toBe(2);
        expect(hashState.openCamera).toBe('CAM_B');
    });

    it('defaults to the first tick and no camera', () => {
        route.url = new URL(SEQUENCE_URL);
        const { hashState } = setup();

        expect(hashState.tick).toBe(1);
        expect(hashState.openCamera).toBeUndefined();
    });

    it('pushes a history entry when a camera opens', () => {
        const { hashState } = setup();

        hashState.setOpenCamera('CAM_B', 'push');

        expect(lastGoto().hash).toBe('#tick=2&camera=CAM_B');
        expect(lastGoto().options).toMatchObject({ replaceState: false, noScroll: true });
    });

    it('replaces the history entry when switching cameras', () => {
        const { hashState } = setup();

        hashState.setOpenCamera('CAM_B', 'replace');

        expect(lastGoto().hash).toBe('#tick=2&camera=CAM_B');
        expect(lastGoto().options).toMatchObject({ replaceState: true });
    });

    it('keeps the camera when the tick changes right after a switch', () => {
        const { hashState } = setup();

        hashState.setOpenCamera('CAM_C', 'replace');
        hashState.setTick(5);

        expect(lastGoto().hash).toBe('#tick=5&camera=CAM_C');
    });

    it('closing after switches pops a single history entry', () => {
        const back = vi.spyOn(history, 'back').mockImplementation(() => {});
        const { hashState } = setup();

        hashState.setOpenCamera('CAM_A', 'push');
        hashState.setOpenCamera('CAM_B', 'replace');
        hashState.setOpenCamera('CAM_C', 'replace');
        vi.mocked(goto).mockClear();
        hashState.setOpenCamera(undefined, 'replace');

        expect(back).toHaveBeenCalledOnce();
        expect(goto).not.toHaveBeenCalled();
        expect(hashState.openCamera).toBeUndefined();
    });

    it('closes a camera from the initial URL by replacing the hash', () => {
        route.url = new URL(`${SEQUENCE_URL}#tick=2&camera=CAM_B`);
        const back = vi.spyOn(history, 'back').mockImplementation(() => {});
        const { hashState } = setup();

        hashState.setOpenCamera(undefined, 'replace');

        expect(back).not.toHaveBeenCalled();
        expect(lastGoto().hash).toBe('#tick=2');
        expect(lastGoto().options).toMatchObject({ replaceState: true });
    });

    it('syncs the camera and tick from the URL after a popstate to another page', () => {
        const { hashState } = setup();
        hashState.setOpenCamera('CAM_A', 'push');

        popstate('http://localhost/other#tick=7');

        expect(hashState.openCamera).toBeUndefined();
        expect(hashState.tick).toBe(7);
    });

    it('keeps the live tick when closing lands on the stale open-time entry', () => {
        vi.spyOn(history, 'back').mockImplementation(() => {});
        const { hashState } = setup();
        hashState.setOpenCamera('CAM_A', 'push');
        hashState.setTick(9);
        hashState.setOpenCamera(undefined, 'replace');

        popstate(`${SEQUENCE_URL}#tick=2`);

        expect(hashState.tick).toBe(9);
        expect(hashState.openCamera).toBeUndefined();
        expect(lastGoto().hash).toBe('#tick=9');
        expect(lastGoto().options).toMatchObject({ replaceState: true });
    });

    it('defers tick writes while history.back is pending', () => {
        vi.spyOn(history, 'back').mockImplementation(() => {});
        const { hashState } = setup();
        hashState.setOpenCamera('CAM_A', 'push');
        hashState.setOpenCamera(undefined, 'replace');
        vi.mocked(goto).mockClear();

        hashState.setTick(10);
        expect(goto).not.toHaveBeenCalled();

        popstate(`${SEQUENCE_URL}#tick=2`);

        expect(goto).toHaveBeenCalledOnce();
        expect(lastGoto().hash).toBe('#tick=10');
    });

    it('applies a hash edited in the address bar', () => {
        const { hashState } = setup();

        route.url = new URL(`${SEQUENCE_URL}#tick=4&camera=CAM_C`);
        flushSync();

        expect(hashState.tick).toBe(4);
        expect(hashState.openCamera).toBe('CAM_C');
        expect(goto).not.toHaveBeenCalled();
    });

    it('ignores URL changes during a navigation', () => {
        const { hashState } = setup();
        hashState.setTick(5);

        route.navigationType = 'goto';
        route.url = new URL(`${SEQUENCE_URL}#tick=4`);
        flushSync();

        expect(hashState.tick).toBe(5);
    });

    it('ignores hash changes while history.back is pending', () => {
        vi.spyOn(history, 'back').mockImplementation(() => {});
        const { hashState } = setup();
        hashState.setOpenCamera('CAM_A', 'push');
        hashState.setTick(9);
        hashState.setOpenCamera(undefined, 'replace');

        route.url = new URL(`${SEQUENCE_URL}#tick=2`);
        flushSync();

        expect(hashState.tick).toBe(9);
    });

    it('drops the tick and camera of the previous sequence', () => {
        const { input, hashState } = setup();
        hashState.setOpenCamera('CAM_A', 'push');
        hashState.setTick(9);

        route.navigationType = 'goto';
        route.url = new URL('http://localhost/datasets/d/mcap/c/mcap-sequences/other');
        input.sequenceId = 'sequence-2';
        flushSync();

        expect(hashState.tick).toBe(1);
        expect(hashState.openCamera).toBeUndefined();
    });
});
