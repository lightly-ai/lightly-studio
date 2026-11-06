import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSmartSelect } from './useSmartSelect.svelte';
import { useReversibleActions } from '$lib/hooks/useReversibleActions';
import { get } from 'svelte/store';

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

const params = $state({ sampleId: 'sample-1' });

const setup = ({ annotationClass = 'cat' }: { annotationClass?: string | null } = {}) => {
    params.sampleId = 'sample-1';
    let smartSelect!: ReturnType<typeof useSmartSelect>;
    cleanup = $effect.root(() => {
        smartSelect = useSmartSelect(() => ({
            collectionId: 'collection-1',
            sampleId: params.sampleId,
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
        vi.resetAllMocks();
        useReversibleActions().clearReversibleActions();
    });

    afterEach(() => cleanup());

    it('requests a preview for a positive point', async () => {
        mocks.mutateAsync.mockResolvedValue({ prediction });
        const smartSelect = setup();

        smartSelect.addPoint({ x: 0.5, y: 0.5, positive: true });

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

        smartSelect.addPoint({ x: 0.5, y: 0.5, positive: true });
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

    it('saves the preview with the selected class and clears it', async () => {
        mocks.mutateAsync.mockResolvedValue({ prediction });
        mocks.saveAnnotationPreviews.mockImplementation(async ({ previews, onPreviewSaved }) =>
            onPreviewSaved(previews[0].preview)
        );
        const smartSelect = setup();
        smartSelect.addPoint({ x: 0.5, y: 0.5, positive: true });
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

    it.each([null, '', '   '])(
        'requires a nonblank selected class: %s',
        async (annotationClass) => {
            mocks.mutateAsync.mockResolvedValue({ prediction });
            const smartSelect = setup({ annotationClass });
            smartSelect.addPoint(point);
            await vi.waitFor(() => expect(smartSelect.preview).toEqual(prediction));
            expect(smartSelect.canSave).toBe(false);
            await smartSelect.save();
            expect(mocks.saveAnnotationPreviews).not.toHaveBeenCalled();
        }
    );

    it('drops the preview once a point is added, even if its request fails', async () => {
        mocks.mutateAsync
            .mockResolvedValueOnce({ prediction })
            .mockRejectedValueOnce(new Error('provider failed'));
        const smartSelect = setup();
        smartSelect.addPoint(point);
        await vi.waitFor(() => expect(smartSelect.canSave).toBe(true));

        smartSelect.addPoint({ ...point, x: 0.6 });
        await vi.waitFor(() => expect(mocks.toastError).toHaveBeenCalled());
        await smartSelect.save();

        expect(smartSelect.preview).toBeNull();
        expect(smartSelect.canSave).toBe(false);
        expect(mocks.saveAnnotationPreviews).not.toHaveBeenCalled();
    });

    it('drops a box preview once a negative point is added', async () => {
        mocks.mutateAsync.mockResolvedValue({ prediction });
        const smartSelect = setup();
        smartSelect.selectBox({ x: 0, y: 0, width: 0.5, height: 0.5 });
        await vi.waitFor(() => expect(smartSelect.canSave).toBe(true));

        smartSelect.addPoint({ ...point, positive: false });

        expect(smartSelect.preview).toBeNull();
        expect(mocks.mutateAsync).toHaveBeenCalledTimes(1);
    });

    it('blocks additional prompts immediately while generating a preview', async () => {
        const pending = deferred();
        mocks.mutateAsync.mockReturnValueOnce(pending.promise);
        const smartSelect = setup();
        smartSelect.addPoint(point);
        expect(smartSelect.isPending).toBe(true);
        smartSelect.addPoint({ ...point, x: 0.6 });
        smartSelect.selectBox({ x: 0, y: 0, width: 0.5, height: 0.5 });
        expect(smartSelect.points).toEqual([point]);
        expect(mocks.mutateAsync).toHaveBeenCalledOnce();
        const undo = useReversibleActions();
        await undo.executeReversibleAction(get(undo.reversibleActions)[0].id);
        expect(smartSelect.isPending).toBe(false);
        pending.resolve({ prediction });
        await pending.promise;
        expect(smartSelect.preview).toBeNull();
        expect(smartSelect.points).toEqual([]);
    });

    it('undoes a failed prompt and a box replacement using the existing undo stack', async () => {
        mocks.mutateAsync.mockResolvedValue({ prediction });
        const smartSelect = setup();
        const undo = useReversibleActions();
        const undoLast = () => undo.executeReversibleAction(get(undo.reversibleActions)[0].id);
        smartSelect.addPoint(point);
        await vi.waitFor(() => expect(smartSelect.preview).toEqual(prediction));
        smartSelect.selectBox({ x: 0, y: 0, width: 0.5, height: 0.5 });
        await vi.waitFor(() => expect(smartSelect.isPending).toBe(false));
        mocks.mutateAsync.mockRejectedValueOnce(new Error('provider failed'));
        smartSelect.addPoint(point);
        await vi.waitFor(() => expect(mocks.toastError).toHaveBeenCalled());
        await undoLast();
        expect(smartSelect.points).toEqual([]);
        expect(smartSelect.box).not.toBeNull();
        expect(smartSelect.preview).toEqual(prediction);
        await undoLast();
        expect(smartSelect.box).toBeNull();
        expect(smartSelect.points).toEqual([point]);
        await undoLast();
        expect(smartSelect.points).toEqual([]);
        expect(smartSelect.preview).toBeNull();
    });

    it('saves only once while a save is in flight', async () => {
        const saving = deferred();
        mocks.mutateAsync.mockResolvedValue({ prediction });
        mocks.saveAnnotationPreviews.mockReturnValue(saving.promise);
        const smartSelect = setup();
        smartSelect.addPoint(point);
        await vi.waitFor(() => expect(smartSelect.canSave).toBe(true));

        const first = smartSelect.save();
        const second = smartSelect.save();
        expect(smartSelect.canSave).toBe(false);
        expect(smartSelect.isSaving).toBe(true);
        saving.resolve(undefined);
        await Promise.all([first, second]);
        expect(smartSelect.isSaving).toBe(false);

        expect(mocks.saveAnnotationPreviews).toHaveBeenCalledTimes(1);
        expect(get(useReversibleActions().reversibleActions)).toEqual([]);
    });

    it('keeps the preview and reports the error when the save fails', async () => {
        mocks.mutateAsync.mockResolvedValue({ prediction });
        mocks.saveAnnotationPreviews.mockRejectedValue(new Error('create failed'));
        const smartSelect = setup();
        smartSelect.addPoint(point);
        await vi.waitFor(() => expect(smartSelect.preview).not.toBeNull());

        await smartSelect.save();

        expect(smartSelect.preview).toEqual(prediction);
        expect(smartSelect.canSave).toBe(true);
        expect(mocks.toastError).toHaveBeenCalledWith(
            'Could not save the annotation: create failed'
        );
    });

    it('keeps the preview when cleared during a failed save', async () => {
        const saving = deferred();
        mocks.mutateAsync.mockResolvedValue({ prediction });
        mocks.saveAnnotationPreviews.mockReturnValue(saving.promise);
        const smartSelect = setup();
        smartSelect.addPoint(point);
        await vi.waitFor(() => expect(smartSelect.canSave).toBe(true));

        const save = smartSelect.save();
        smartSelect.clear();
        saving.reject(new Error('create failed'));
        await save;

        expect(smartSelect.preview).toEqual(prediction);
        expect(smartSelect.canSave).toBe(true);
    });

    it('drops the box preview when a negative point follows a box', async () => {
        mocks.mutateAsync.mockResolvedValue({ prediction });
        const smartSelect = setup();
        smartSelect.selectBox({ x: 0, y: 0, width: 0.5, height: 0.5 });
        await vi.waitFor(() => expect(smartSelect.preview).toEqual(prediction));

        smartSelect.addPoint({ ...point, positive: false });

        expect(smartSelect.preview).toBeNull();
        expect(smartSelect.canSave).toBe(false);
        expect(mocks.mutateAsync).toHaveBeenCalledOnce();
    });

    it('drops the prompts and a pending response of a previous sample', async () => {
        const pending = deferred();
        mocks.mutateAsync.mockReturnValueOnce(pending.promise);
        const smartSelect = setup();

        smartSelect.addPoint(point);
        params.sampleId = 'sample-2';
        flushSync();
        pending.resolve({ prediction });
        await pending.promise;

        expect(smartSelect.points).toEqual([]);
        expect(smartSelect.preview).toBeNull();
        expect(get(useReversibleActions().reversibleActions)).toEqual([]);
    });

    it('drops a pending response once torn down', async () => {
        const pending = deferred();
        mocks.mutateAsync.mockReturnValueOnce(pending.promise);
        const smartSelect = setup();

        smartSelect.addPoint(point);
        cleanup();
        pending.reject(new Error('provider failed'));
        await pending.promise.catch(() => undefined);

        expect(mocks.toastError).not.toHaveBeenCalled();
    });
});
