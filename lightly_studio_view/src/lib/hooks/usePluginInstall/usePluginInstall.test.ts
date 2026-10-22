import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { getPluginInstallJob, installPlugin } from '$lib/api/lightly_studio_local';
import { isInstalling, POLL_INTERVAL_MS, usePluginInstall } from './usePluginInstall';

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@tanstack/svelte-query')>()),
    useQueryClient: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local')>()),
    installPlugin: vi.fn(),
    getPluginInstallJob: vi.fn()
}));

vi.mock('svelte-sonner', () => ({
    toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() }
}));

type InstallResult = Awaited<ReturnType<typeof installPlugin>>;
type JobResult = Awaited<ReturnType<typeof getPluginInstallJob>>;

const job = (status: string, extra: Record<string, unknown> = {}) => ({
    data: { job_id: 'job-1', plugin_id: 'p', status, ...extra }
});

describe('usePluginInstall', () => {
    const invalidateQueries = vi.fn();

    beforeEach(() => {
        vi.useFakeTimers();
        vi.clearAllMocks();
        vi.mocked(useQueryClient).mockReturnValue({
            invalidateQueries
        } as unknown as ReturnType<typeof useQueryClient>);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('polls the job until it succeeds and refreshes the plugin lists', async () => {
        vi.mocked(installPlugin).mockResolvedValue(job('queued') as unknown as InstallResult);
        vi.mocked(getPluginInstallJob)
            .mockResolvedValueOnce(job('running') as unknown as JobResult)
            .mockResolvedValueOnce(
                job('succeeded', { new_operator_ids: ['op'] }) as unknown as JobResult
            );
        const { jobs, install } = usePluginInstall();

        const done = install({ id: 'p', name: 'Demo' });
        await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
        expect(isInstalling(get(jobs)['p'])).toBe(true);
        await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
        await done;

        expect(get(jobs)['p'].status).toBe('succeeded');
        expect(getPluginInstallJob).toHaveBeenCalledTimes(2);
        expect(invalidateQueries).toHaveBeenCalledTimes(2);
        expect(toast.success).toHaveBeenCalledWith('Demo is ready', expect.anything());
    });

    it('reports a refused install without polling', async () => {
        vi.mocked(installPlugin).mockResolvedValue({
            data: undefined,
            error: { error: 'Plugin installs are only allowed from the machine' }
        } as unknown as InstallResult);
        const { jobs, install } = usePluginInstall();

        await install({ id: 'p', name: 'Demo' });

        expect(get(jobs)['p'].status).toBe('failed');
        expect(getPluginInstallJob).not.toHaveBeenCalled();
        expect(toast.error).toHaveBeenCalledWith('Could not install Demo', {
            description: 'Plugin installs are only allowed from the machine'
        });
    });

    it('reports a failed install job', async () => {
        vi.mocked(installPlugin).mockResolvedValue(job('queued') as unknown as InstallResult);
        vi.mocked(getPluginInstallJob).mockResolvedValue(
            job('failed', {
                error_message: 'The installer exited with code 1.'
            }) as unknown as JobResult
        );
        const { install } = usePluginInstall();

        const done = install({ id: 'p', name: 'Demo' });
        await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
        await done;

        expect(toast.error).toHaveBeenCalledWith('Could not install Demo', {
            description: 'The installer exited with code 1.'
        });
    });
});
