import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLaunchSource } from './useLaunchSource';
import type { LaunchSource } from '$lib/api/lightly_studio_local';
import * as sdkModule from '$lib/api/lightly_studio_local/sdk.gen';

const mockTrackEvent = vi.fn();
const mockRegisterSuperProperties = vi.fn();

vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({
        trackEvent: mockTrackEvent,
        registerSuperProperties: mockRegisterSuperProperties
    })
}));

const mockLaunchSourceResponse = (launch_source: LaunchSource) =>
    vi.spyOn(sdkModule, 'getLaunchSource').mockResolvedValueOnce({
        data: { launch_source },
        request: new Request('http://localhost'),
        response: new Response()
    });

describe('useLaunchSource', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should track the quickstart event when the app was started by quickstart', async () => {
        mockLaunchSourceResponse('quickstart');

        await useLaunchSource().trackLaunchSource();

        expect(mockRegisterSuperProperties).toHaveBeenCalledWith({ launch_source: 'quickstart' });
        expect(mockTrackEvent).toHaveBeenCalledWith('quickstart_launched');
    });

    it('should only register the super property for other launch sources', async () => {
        mockLaunchSourceResponse('sdk');

        await useLaunchSource().trackLaunchSource();

        expect(mockRegisterSuperProperties).toHaveBeenCalledWith({ launch_source: 'sdk' });
        expect(mockTrackEvent).not.toHaveBeenCalled();
    });

    it('should not throw or track anything when the request fails', async () => {
        vi.spyOn(sdkModule, 'getLaunchSource').mockRejectedValueOnce(new Error('API Error'));

        await expect(useLaunchSource().trackLaunchSource()).resolves.toBeUndefined();

        expect(mockRegisterSuperProperties).not.toHaveBeenCalled();
        expect(mockTrackEvent).not.toHaveBeenCalled();
    });
});
