import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { encodeModel } from '$lib/browserInference/testHelpers';

const createDetector = vi.fn();
const fetchModelBytes = vi.fn();

vi.mock('$lib/browserInference', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/browserInference')>()),
    createDetector,
    fetchModelBytes
}));

// jsdom's Blob has no arrayBuffer(), which every browser has.
Blob.prototype.arrayBuffer ??= function (this: Blob) {
    return new Promise<ArrayBuffer>((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as ArrayBuffer);
        reader.readAsArrayBuffer(this);
    });
};

// The store is module-level, so each test loads a fresh copy.
const loadHook = async () => (await import('./useBrowserModels')).useBrowserModels();

describe('useBrowserModels', () => {
    beforeEach(() => {
        vi.resetModules();
        createDetector.mockReset().mockResolvedValue({ classNames: ['person', 'car'] });
        fetchModelBytes.mockReset().mockImplementation(async (_url, onProgress) => {
            onProgress(5, 10);
            return new Uint8Array();
        });
    });

    it('lists the default model before anything loads', async () => {
        const { models } = await loadHook();

        expect(get(models)).toEqual([
            { id: 'ltdetrv2-s-coco', task: 'object_detection', class_names: [], runsIn: 'browser' }
        ]);
    });

    it('creates one detector per model and fills its classes', async () => {
        const { getDetector, models } = await loadHook();

        await Promise.all([getDetector('ltdetrv2-s-coco'), getDetector('ltdetrv2-s-coco')]);

        expect(createDetector).toHaveBeenCalledTimes(1);
        expect(get(models)[0].class_names).toEqual(['person', 'car']);
    });

    it('reports the download progress and clears it once loaded', async () => {
        const { getDetector, loadProgress } = await loadHook();
        const progress: unknown[] = [];
        const unsubscribe = loadProgress.subscribe((value) => progress.push(value));

        await getDetector('ltdetrv2-s-coco');
        unsubscribe();

        expect(progress).toContainEqual({ modelId: 'ltdetrv2-s-coco', loaded: 5, total: 10 });
        expect(progress.at(-1)).toBeNull();
    });

    it('adds a model file with classes from its metadata', async () => {
        const { addModelFile, models } = await loadHook();
        const file = new File([encodeModel({ classes: '{"0":"forklift"}' })], 'forklifts.onnx');

        const id = await addModelFile(file);

        expect(id).toBe('forklifts');
        expect(get(models).find((model) => model.id === id)?.class_names).toEqual(['forklift']);
    });

    it('gives a second file with the same name a new id', async () => {
        const { addModelFile } = await loadHook();
        const bytes = encodeModel({ classes: '{"0":"forklift"}' });

        await addModelFile(new File([bytes], 'forklifts.onnx'));
        const secondId = await addModelFile(new File([bytes], 'forklifts.onnx'));

        expect(secondId).toBe('forklifts-2');
    });
});
