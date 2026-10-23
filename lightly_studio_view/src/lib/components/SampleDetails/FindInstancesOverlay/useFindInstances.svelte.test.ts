import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useFindInstances } from './useFindInstances.svelte';

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

const makePrediction = (x: number) => ({
    bbox: { x, y: 0, width: 1, height: 1 },
    segmentation_mask: [x, 1],
    score: null
});
const first = makePrediction(1);
const second = makePrediction(2);

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

const setup = (initialPrompt = 'cars') => {
    const params = $state<{ sampleId: string; prompt: string; annotationClass: string | null }>({
        sampleId: 'sample-1',
        prompt: initialPrompt,
        annotationClass: null
    });
    const onSaved = vi.fn();
    let instances!: ReturnType<typeof useFindInstances>;
    cleanup = $effect.root(() => {
        instances = useFindInstances(() => ({
            collectionId: 'collection-1',
            sampleId: params.sampleId,
            prompt: params.prompt,
            maxInstances: 8,
            saveAs: 'box',
            annotationClass: params.annotationClass,
            annotationSource: 'source',
            onSaved
        }));
    });
    flushSync();
    return { instances, params, onSaved };
};

const generateResults = async (instances: ReturnType<typeof useFindInstances>) => {
    mocks.mutateAsync.mockResolvedValueOnce({ predictions: [first, second] });
    await instances.generate();
    expect(instances.predictions).toHaveLength(2);
};

describe('useFindInstances', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => cleanup());

    it('requests instances for the prompt and the drawn boxes', async () => {
        const { instances } = setup(' cars ');
        const box = { x: 0.1, y: 0.1, width: 0.2, height: 0.2 };
        instances.addBox(box);

        await generateResults(instances);

        expect(mocks.mutateAsync).toHaveBeenCalledWith({
            body: {
                collection_id: 'collection-1',
                sample_id: 'sample-1',
                text_prompt: 'cars',
                boxes: [box],
                max_instances: 8
            }
        });
        expect(instances.boxes).toEqual([]);
        expect(instances.isGenerating).toBe(false);
    });

    it('keeps the drawn boxes when no instances are found', async () => {
        const { instances } = setup();
        const box = { x: 0.1, y: 0.1, width: 0.2, height: 0.2 };
        instances.addBox(box);
        mocks.mutateAsync.mockResolvedValueOnce({ predictions: [] });

        await instances.generate();

        expect(instances.boxes).toEqual([box]);
    });

    it('does not request instances with boxes but without a prompt', async () => {
        const { instances } = setup('  ');
        instances.addBox({ x: 0.1, y: 0.1, width: 0.2, height: 0.2 });

        await instances.generate();

        expect(mocks.mutateAsync).not.toHaveBeenCalled();
    });

    it('drops the results but keeps the drawn boxes when the prompt changes', async () => {
        const { instances, params } = setup();
        await generateResults(instances);
        const box = { x: 0.1, y: 0.1, width: 0.2, height: 0.2 };
        instances.addBox(box);

        params.prompt = 'trucks';
        flushSync();

        expect(instances.predictions).toEqual([]);
        expect(instances.boxes).toEqual([box]);
    });

    it('keeps the results when only whitespace around the prompt changes', async () => {
        const { instances, params } = setup();
        await generateResults(instances);

        params.prompt = 'cars ';
        flushSync();

        expect(instances.predictions).toHaveLength(2);
    });

    it('requests instances only once while a request is in flight', async () => {
        const pending = deferred();
        mocks.mutateAsync.mockReturnValueOnce(pending.promise);
        const { instances } = setup();

        const request = instances.generate();
        await instances.generate();
        pending.resolve({ predictions: [] });
        await request;

        expect(mocks.mutateAsync).toHaveBeenCalledTimes(1);
    });

    it('does not save while instances are being found', async () => {
        const pending = deferred();
        const { instances } = setup();
        await generateResults(instances);
        mocks.mutateAsync.mockReturnValueOnce(pending.promise);

        const request = instances.generate();
        expect(instances.canSave).toBe(false);
        await instances.save();
        pending.resolve({ predictions: [second] });
        await request;

        expect(mocks.saveAnnotationPreviews).not.toHaveBeenCalled();
        expect(instances.predictions).toEqual([second]);
    });

    it('drops a response and an error that arrive after a clear', async () => {
        const success = deferred();
        const failure = deferred();
        mocks.mutateAsync.mockReturnValueOnce(success.promise);
        mocks.mutateAsync.mockReturnValueOnce(failure.promise);
        const { instances } = setup();

        const firstRequest = instances.generate();
        instances.clear();
        success.resolve({ predictions: [first] });
        const secondRequest = instances.generate();
        instances.clear();
        failure.reject(new Error('provider failed'));
        await Promise.all([firstRequest, secondRequest]);

        expect(instances.predictions).toEqual([]);
        expect(instances.isGenerating).toBe(false);
        expect(mocks.toastError).not.toHaveBeenCalled();
    });

    it('saves the instances and removes each saved one', async () => {
        const { instances } = setup();
        await generateResults(instances);
        mocks.saveAnnotationPreviews.mockImplementation(async ({ previews, onPreviewSaved }) =>
            previews.forEach(({ preview }: { preview: unknown }) => onPreviewSaved(preview))
        );

        await instances.save();

        expect(mocks.saveAnnotationPreviews).toHaveBeenCalledWith(
            expect.objectContaining({
                sampleId: 'sample-1',
                saveAs: 'box',
                annotationSource: 'source',
                previews: [
                    { preview: first, className: 'cars' },
                    { preview: second, className: 'cars' }
                ]
            })
        );
        expect(instances.predictions).toEqual([]);
    });

    it('keeps only the unsaved instances when a save fails', async () => {
        const { instances } = setup();
        await generateResults(instances);
        mocks.saveAnnotationPreviews.mockImplementation(async ({ previews, onPreviewSaved }) => {
            onPreviewSaved(previews[0].preview);
            throw new Error('create failed');
        });

        await instances.save();

        expect(instances.predictions).toEqual([second]);
        expect(instances.canSave).toBe(true);
        expect(mocks.toastError).toHaveBeenCalledWith(
            'Could not save the annotations: create failed'
        );
    });

    it('drops the unsaved instances when cleared during a failing save', async () => {
        const saving = deferred();
        const { instances, params } = setup();
        await generateResults(instances);
        mocks.saveAnnotationPreviews.mockImplementation(async ({ previews, onPreviewSaved }) => {
            onPreviewSaved(previews[0].preview);
            await saving.promise;
        });

        const save = instances.save();
        instances.clear();
        params.prompt = '';
        flushSync();
        expect(instances.predictions).toEqual([second]);
        saving.reject(new Error('create failed'));
        await save;

        expect(instances.predictions).toEqual([]);
    });

    it('saves only once while a save is in flight', async () => {
        const saving = deferred();
        const { instances } = setup();
        await generateResults(instances);
        mocks.saveAnnotationPreviews.mockReturnValue(saving.promise);

        const firstSave = instances.save();
        const secondSave = instances.save();
        expect(instances.canSave).toBe(false);
        saving.resolve(undefined);
        await Promise.all([firstSave, secondSave]);

        expect(mocks.saveAnnotationPreviews).toHaveBeenCalledTimes(1);
    });

    it('keeps the prediction in the list while a save is in flight', async () => {
        const saving = deferred();
        const { instances } = setup();
        await generateResults(instances);
        mocks.saveAnnotationPreviews.mockReturnValue(saving.promise);

        const save = instances.save();
        instances.removePrediction(instances.predictions[0]);

        expect(instances.predictions).toEqual([first, second]);
        saving.resolve(undefined);
        await save;
    });

    it('saves with a class picked after the results were generated', async () => {
        const { instances, params } = setup('car');
        await generateResults(instances);
        params.annotationClass = 'truck';
        flushSync();
        mocks.saveAnnotationPreviews.mockResolvedValueOnce(undefined);

        await instances.save();

        expect(mocks.saveAnnotationPreviews).toHaveBeenCalledWith(
            expect.objectContaining({
                previews: [
                    { preview: first, className: 'truck' },
                    { preview: second, className: 'truck' }
                ]
            })
        );
    });

    it('drops the results of a previous sample while a save runs', async () => {
        const saving = deferred();
        const { instances, params } = setup();
        await generateResults(instances);
        mocks.saveAnnotationPreviews.mockReturnValue(saving.promise);
        const save = instances.save();

        params.sampleId = 'sample-2';
        flushSync();

        expect(instances.predictions).toEqual([]);
        saving.resolve(undefined);
        await save;
    });

    it('drops a pending response once torn down', async () => {
        const pending = deferred();
        mocks.mutateAsync.mockReturnValueOnce(pending.promise);
        const { instances } = setup();

        const request = instances.generate();
        cleanup();
        pending.reject(new Error('provider failed'));
        await request;

        expect(mocks.toastError).not.toHaveBeenCalled();
    });

    it('skips the callbacks of a save that ends after teardown', async () => {
        const saving = deferred();
        const { instances, onSaved } = setup();
        await generateResults(instances);
        mocks.saveAnnotationPreviews.mockReturnValue(saving.promise);

        const save = instances.save();
        cleanup();
        saving.resolve(undefined);
        await save;

        expect(onSaved).not.toHaveBeenCalled();
    });
});
