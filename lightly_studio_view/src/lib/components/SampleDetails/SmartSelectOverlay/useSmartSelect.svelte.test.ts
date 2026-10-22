import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSmartSelect } from './useSmartSelect.svelte';

const mocks = vi.hoisted(() => ({
    mutateAsync: vi.fn(),
    saveAnnotationPreviews: vi.fn(),
    toastError: vi.fn()
}));

vi.mock('@tanstack/svelte-query', () => ({
    createMutation: () => ({ mutateAsync: mocks.mutateAsync })
}));
vi.mock('$lib/hooks', () => ({
    useSaveAnnotationPreviews: () => ({ saveAnnotationPreviews: mocks.saveAnnotationPreviews })
}));
vi.mock('svelte-sonner', () => ({ toast: { error: mocks.toastError } }));

const prediction = {
    bbox: { x: 0, y: 0, width: 1, height: 1 },
    segmentation_mask: [0, 1],
    score: null
};

const deferred = () => {
    let resolve: (value: unknown) => void = () => undefined;
    let reject: (error: unknown) => void = () => undefined;
    const promise = new Promise((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return { promise, resolve, reject };
};

let cleanup = () => {};

const setup = ({ annotationClass = null }: { annotationClass?: string | null } = {}) => {
    let smartSelect!: ReturnType<typeof useSmartSelect>;
    cleanup = $effect.root(() => {
        smartSelect = useSmartSelect(() => ({
            collectionId: 'collection-1',
            sampleId: 'sample-1',
            saveAs: 'mask',
            annotationClass,
            annotationSource: 'source',
            onSaved: vi.fn()
        }));
    });
    flushSync();
    return smartSelect;
};

const point = { x: 0.5, y: 0.5, positive: true };

describe('useSmartSelect', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => cleanup());

    it('requests a preview for a positive point', async () => {
        mocks.mutateAsync.mockResolvedValue({ prediction });
        const smartSelect = setup();

        smartSelect.addPoint({ x: 0.5, y: 0.5, positive: true }, null);

        await vi.waitFor(() => expect(smartSelect.preview).toEqual(prediction));
        expect(mocks.mutateAsync).toHaveBeenCalledWith({
            body: {
                collection_id: 'collection-1',
                sample_id: 'sample-1',
                points: [{ x: 0.5, y: 0.5, positive: true }]
            }
        });
    });

    it('drops a response and an error that arrive after a clear', async () => {
        const success = deferred();
        const failure = deferred();
        mocks.mutateAsync.mockReturnValueOnce(success.promise);
        mocks.mutateAsync.mockReturnValueOnce(failure.promise);
        const smartSelect = setup();

        smartSelect.addPoint({ x: 0.5, y: 0.5, positive: true }, null);
        smartSelect.clear();
        success.resolve({ prediction });
        smartSelect.selectBox({ x: 0, y: 0, width: 0.5, height: 0.5 });
        smartSelect.clear();
        failure.reject(new Error('provider failed'));
        await Promise.allSettled([success.promise, failure.promise]);

        expect(smartSelect.preview).toBeNull();
        expect(smartSelect.points).toEqual([]);
        expect(mocks.toastError).not.toHaveBeenCalled();
    });

    it('saves the preview with the hinted class and clears it', async () => {
        mocks.mutateAsync.mockResolvedValue({ prediction });
        mocks.saveAnnotationPreviews.mockImplementation(async ({ previews, onPreviewSaved }) =>
            onPreviewSaved(previews[0].preview)
        );
        const smartSelect = setup();
        smartSelect.addPoint({ x: 0.5, y: 0.5, positive: true }, 'cat');
        await vi.waitFor(() => expect(smartSelect.preview).not.toBeNull());

        await smartSelect.save();

        expect(mocks.saveAnnotationPreviews).toHaveBeenCalledWith(
            expect.objectContaining({
                sampleId: 'sample-1',
                saveAs: 'mask',
                annotationSource: 'source',
                previews: [{ preview: prediction, className: 'cat' }]
            })
        );
        expect(smartSelect.preview).toBeNull();
    });

    it('saves the selected class even when its name is empty', async () => {
        mocks.mutateAsync.mockResolvedValue({ prediction });
        const smartSelect = setup({ annotationClass: '' });
        smartSelect.addPoint(point, 'cat');
        await vi.waitFor(() => expect(smartSelect.canSave).toBe(true));

        await smartSelect.save();

        expect(mocks.saveAnnotationPreviews).toHaveBeenCalledWith(
            expect.objectContaining({ previews: [{ preview: prediction, className: '' }] })
        );
    });

    it('does not save while a newer preview is pending', async () => {
        const newer = deferred();
        mocks.mutateAsync.mockResolvedValueOnce({ prediction }).mockReturnValueOnce(newer.promise);
        const smartSelect = setup();
        smartSelect.addPoint(point, null);
        await vi.waitFor(() => expect(smartSelect.canSave).toBe(true));

        smartSelect.addPoint({ ...point, x: 0.6 }, null);
        expect(smartSelect.canSave).toBe(false);
        await smartSelect.save();
        expect(mocks.saveAnnotationPreviews).not.toHaveBeenCalled();

        newer.resolve({ prediction });
        await vi.waitFor(() => expect(smartSelect.canSave).toBe(true));
    });

    it('keeps the newest preview when an older response arrives late', async () => {
        const older = deferred();
        const newer = { ...prediction, score: 0.9 };
        mocks.mutateAsync.mockReturnValueOnce(older.promise).mockResolvedValueOnce({
            prediction: newer
        });
        const smartSelect = setup();

        smartSelect.addPoint(point, null);
        smartSelect.addPoint({ ...point, x: 0.6 }, null);
        await vi.waitFor(() => expect(smartSelect.preview).toEqual(newer));
        older.resolve({ prediction });
        await older.promise;

        expect(smartSelect.preview).toEqual(newer);
    });

    it('saves only once while a save is in flight', async () => {
        const saving = deferred();
        mocks.mutateAsync.mockResolvedValue({ prediction });
        mocks.saveAnnotationPreviews.mockReturnValue(saving.promise);
        const smartSelect = setup();
        smartSelect.addPoint(point, null);
        await vi.waitFor(() => expect(smartSelect.canSave).toBe(true));

        const first = smartSelect.save();
        const second = smartSelect.save();
        expect(smartSelect.canSave).toBe(false);
        saving.resolve(undefined);
        await Promise.all([first, second]);

        expect(mocks.saveAnnotationPreviews).toHaveBeenCalledTimes(1);
    });

    it('keeps the preview and reports the error when the save fails', async () => {
        mocks.mutateAsync.mockResolvedValue({ prediction });
        mocks.saveAnnotationPreviews.mockRejectedValue(new Error('create failed'));
        const smartSelect = setup();
        smartSelect.addPoint(point, null);
        await vi.waitFor(() => expect(smartSelect.preview).not.toBeNull());

        await smartSelect.save();

        expect(smartSelect.preview).toEqual(prediction);
        expect(smartSelect.canSave).toBe(true);
        expect(mocks.toastError).toHaveBeenCalledWith(
            'Could not save the annotation: create failed'
        );
    });

    it('drops a pending response once torn down', async () => {
        const pending = deferred();
        mocks.mutateAsync.mockReturnValueOnce(pending.promise);
        const smartSelect = setup();

        smartSelect.addPoint(point, null);
        cleanup();
        pending.reject(new Error('provider failed'));
        await pending.promise.catch(() => undefined);

        expect(mocks.toastError).not.toHaveBeenCalled();
    });
});
