import { beforeEach, describe, expect, it, vi } from 'vitest';
import { prepareAnnotationImage } from '$lib/api/lightly_studio_local';
import { usePrepareAnnotationImage } from './usePrepareAnnotationImage';

vi.mock('$lib/api/lightly_studio_local', () => ({
    prepareAnnotationImage: vi.fn()
}));

const prepareMock = vi.mocked(prepareAnnotationImage);

describe('usePrepareAnnotationImage', () => {
    beforeEach(() => {
        prepareMock.mockReset();
    });

    it('prepares each sample only once', async () => {
        prepareMock.mockResolvedValue({} as Awaited<ReturnType<typeof prepareAnnotationImage>>);
        const { prepareImage } = usePrepareAnnotationImage();

        prepareImage({ collectionId: 'c', sampleId: 'once-1' });
        prepareImage({ collectionId: 'c', sampleId: 'once-1' });
        prepareImage({ collectionId: 'c', sampleId: 'once-2' });
        await Promise.resolve();

        expect(prepareMock).toHaveBeenCalledTimes(2);
        expect(prepareMock).toHaveBeenCalledWith({
            body: { collection_id: 'c', sample_id: 'once-1' },
            throwOnError: true
        });
    });

    it('logs a failure and retries on the next activation', async () => {
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
        prepareMock.mockRejectedValueOnce({ error: 'Provider unavailable' });
        const { prepareImage } = usePrepareAnnotationImage();

        prepareImage({ collectionId: 'c', sampleId: 'retry' });
        await vi.waitFor(() => expect(warn).toHaveBeenCalled());
        prepareMock.mockResolvedValue({} as Awaited<ReturnType<typeof prepareAnnotationImage>>);
        prepareImage({ collectionId: 'c', sampleId: 'retry' });

        expect(prepareMock).toHaveBeenCalledTimes(2);
        warn.mockRestore();
    });
});
