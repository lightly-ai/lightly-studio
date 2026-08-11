import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLaunchSource } from './useLaunchSource';
import type { LaunchSource } from '$lib/api/lightly_studio_local';
import * as sdkModule from '$lib/api/lightly_studio_local/sdk.gen';

const mockTrackEvent = vi.fn();
const mockRegisterSessionProperties = vi.fn();

vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({
        trackEvent: mockTrackEvent,
        registerSessionProperties: mockRegisterSessionProperties
    })
}));

const REPORTED_LAUNCH_ID_KEY = 'lightlyStudio_reportedLaunchId';
const LAUNCH_ID = '019ff167-b775-76b8-9b09-c2fd260c67c1';
const OTHER_LAUNCH_ID = '2b4d1e7c-9a3f-4c21-8e55-7d0a1f6b3c88';

const mockLaunchSourceResponse = (launchSource: LaunchSource, launchId = LAUNCH_ID) =>
    vi.spyOn(sdkModule, 'getLaunchSource').mockResolvedValueOnce({
        data: { launch_source: launchSource, launch_id: launchId },
        request: new Request('http://localhost'),
        response: new Response()
    });

// This environment provides `localStorage` as a bare object with no methods, so tests that care
// about persistence install a working one.
const createMemoryStorage = () => {
    const entries = new Map<string, string>();
    return {
        getItem: (key: string) => entries.get(key) ?? null,
        setItem: (key: string, value: string) => void entries.set(key, value),
        removeItem: (key: string) => void entries.delete(key),
        clear: () => entries.clear(),
        key: () => null,
        length: 0
    };
};

describe('useLaunchSource', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
        vi.clearAllMocks();
        vi.stubGlobal('localStorage', createMemoryStorage());
    });

    it('should track the quickstart event when the app was started by quickstart', async () => {
        mockLaunchSourceResponse('quickstart');

        await useLaunchSource().trackLaunchSource();

        expect(mockRegisterSessionProperties).toHaveBeenCalledWith({ launch_source: 'quickstart' });
        expect(mockTrackEvent).toHaveBeenCalledWith('quickstart_launched', {
            launch_id: LAUNCH_ID
        });
        expect(localStorage.getItem(REPORTED_LAUNCH_ID_KEY)).toBe(LAUNCH_ID);
    });

    it('should not track the same launch twice', async () => {
        localStorage.setItem(REPORTED_LAUNCH_ID_KEY, LAUNCH_ID);
        mockLaunchSourceResponse('quickstart');

        await useLaunchSource().trackLaunchSource();

        expect(mockRegisterSessionProperties).toHaveBeenCalledWith({ launch_source: 'quickstart' });
        expect(mockTrackEvent).not.toHaveBeenCalled();
    });

    it('should track a new launch after a previous one was reported', async () => {
        localStorage.setItem(REPORTED_LAUNCH_ID_KEY, OTHER_LAUNCH_ID);
        mockLaunchSourceResponse('quickstart');

        await useLaunchSource().trackLaunchSource();

        expect(mockTrackEvent).toHaveBeenCalledWith('quickstart_launched', {
            launch_id: LAUNCH_ID
        });
        expect(localStorage.getItem(REPORTED_LAUNCH_ID_KEY)).toBe(LAUNCH_ID);
    });

    it('should only register the session property for other launch sources', async () => {
        mockLaunchSourceResponse('sdk');

        await useLaunchSource().trackLaunchSource();

        expect(mockRegisterSessionProperties).toHaveBeenCalledWith({ launch_source: 'sdk' });
        expect(mockTrackEvent).not.toHaveBeenCalled();
        expect(localStorage.getItem(REPORTED_LAUNCH_ID_KEY)).toBeNull();
    });

    it('should track the launch when localStorage is unavailable', async () => {
        vi.stubGlobal('localStorage', {
            getItem: () => {
                throw new Error('storage disabled');
            },
            setItem: () => {
                throw new Error('storage disabled');
            }
        });
        mockLaunchSourceResponse('quickstart');

        await useLaunchSource().trackLaunchSource();

        expect(mockTrackEvent).toHaveBeenCalledWith('quickstart_launched', {
            launch_id: LAUNCH_ID
        });
    });

    it('should not throw or track anything when the request fails', async () => {
        vi.spyOn(sdkModule, 'getLaunchSource').mockRejectedValueOnce(new Error('API Error'));

        await expect(useLaunchSource().trackLaunchSource()).resolves.toBeUndefined();

        expect(mockRegisterSessionProperties).not.toHaveBeenCalled();
        expect(mockTrackEvent).not.toHaveBeenCalled();
    });
});
