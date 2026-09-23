import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { triggerDownload, useExportDownload } from './useExportDownload';

describe('triggerDownload', () => {
    it('creates a temporary anchor, sets href, and clicks it', () => {
        const anchor = document.createElement('a');
        vi.spyOn(document, 'createElement').mockReturnValue(anchor as HTMLAnchorElement);
        vi.spyOn(document.body, 'appendChild').mockImplementation(() => anchor);
        vi.spyOn(document.body, 'removeChild').mockImplementation(() => anchor);
        const click = vi.spyOn(anchor, 'click').mockImplementation(() => undefined);

        triggerDownload('https://example.com/export.zip');

        expect(anchor.href).toBe('https://example.com/export.zip');
        expect(click).toHaveBeenCalledOnce();
        expect(document.body.appendChild).toHaveBeenCalledWith(anchor);
        expect(document.body.removeChild).toHaveBeenCalledWith(anchor);
    });
});

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
