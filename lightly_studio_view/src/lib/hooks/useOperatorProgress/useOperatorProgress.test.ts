import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { get } from 'svelte/store';
import type { OperatorProgress } from '$lib/api/lightly_studio_local';
import { useOperatorProgress } from './useOperatorProgress';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    getOperatorRunProgress: vi.fn()
}));

const { getOperatorRunProgress } = await import('$lib/api/lightly_studio_local/sdk.gen');

const RUN_ID = '11111111-1111-1111-1111-111111111111';

function mockProgressResponse(progress: OperatorProgress) {
    vi.mocked(getOperatorRunProgress).mockResolvedValue({
        data: progress,
        error: undefined,
        request: {} as Request,
        response: {} as Response
    });
}

/** The backend answers 404 until the run reports, and again once it finishes. */
function mockNoProgressResponse() {
    vi.mocked(getOperatorRunProgress).mockResolvedValue({
        data: undefined,
        error: { detail: [] },
        request: {} as Request,
        response: {} as Response
    });
}

describe('useOperatorProgress', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('starts with no progress', () => {
        const { progress } = useOperatorProgress();

        expect(get(progress)).toBeNull();
    });

    it('polls the reported progress of a run', async () => {
        mockProgressResponse({ current: 5, total: 10, description: 'Running inference' });
        const { progress, startPolling, stopPolling } = useOperatorProgress();

        startPolling(RUN_ID);
        await vi.advanceTimersByTimeAsync(500);

        expect(getOperatorRunProgress).toHaveBeenCalledWith({ path: { run_id: RUN_ID } });
        expect(get(progress)).toEqual({
            current: 5,
            total: 10,
            description: 'Running inference'
        });

        stopPolling();
    });

    it('reports no progress while the run is unknown to the backend', async () => {
        mockNoProgressResponse();
        const { progress, startPolling, stopPolling } = useOperatorProgress();

        startPolling(RUN_ID);
        await vi.advanceTimersByTimeAsync(500);

        expect(get(progress)).toBeNull();

        stopPolling();
    });

    it('stops polling and clears progress', async () => {
        mockProgressResponse({ current: 5, total: 10, description: '' });
        const { progress, startPolling, stopPolling } = useOperatorProgress();
        startPolling(RUN_ID);
        await vi.advanceTimersByTimeAsync(500);

        stopPolling();
        vi.mocked(getOperatorRunProgress).mockClear();
        await vi.advanceTimersByTimeAsync(2000);

        expect(get(progress)).toBeNull();
        expect(getOperatorRunProgress).not.toHaveBeenCalled();
    });
});
