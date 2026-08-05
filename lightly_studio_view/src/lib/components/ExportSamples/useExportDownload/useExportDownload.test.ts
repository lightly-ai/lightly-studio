import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useExportDownload } from './useExportDownload';

describe('useExportDownload', () => {
    beforeEach(vi.resetAllMocks);

    it('calls prepare when handleDownload is called', async () => {
        const prepare = vi.fn().mockResolvedValue(undefined);
        const { handleDownload } = useExportDownload(prepare);
        await handleDownload();
        expect(prepare).toHaveBeenCalledOnce();
    });

    it('sets isLoading to true while prepare is pending and false after', async () => {
        let resolve!: () => void;
        const prepare = vi.fn().mockReturnValue(
            new Promise<void>((r) => {
                resolve = r;
            })
        );
        const { isLoading, handleDownload } = useExportDownload(prepare);

        const downloadPromise = handleDownload();
        expect(get(isLoading)).toBe(true);
        resolve();
        await downloadPromise;
        expect(get(isLoading)).toBe(false);
    });

    it('sets errorMessage when prepare throws', async () => {
        const prepare = vi.fn().mockRejectedValue(new Error('API error'));
        const { errorMessage, handleDownload } = useExportDownload(prepare);
        await handleDownload();
        expect(get(errorMessage)).toBe('Export failed: Error: API error');
    });

    it('clears errorMessage at the start of the next download attempt', async () => {
        const prepare = vi
            .fn()
            .mockRejectedValueOnce(new Error('fail'))
            .mockResolvedValueOnce(undefined);
        const { errorMessage, handleDownload } = useExportDownload(prepare);
        await handleDownload();
        expect(get(errorMessage)).toBe('Export failed: Error: fail');
        await handleDownload();
        expect(get(errorMessage)).toBe('');
    });
});
