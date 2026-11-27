import { describe, expect, it, vi } from 'vitest';
import { runBatchAutoLabel } from './runBatchAutoLabel';

const person = {
    class_name: 'person',
    bbox: { x: 0, y: 0, width: 1, height: 1 },
    segmentation_mask: null,
    score: 0.9
};
const car = { ...person, class_name: 'car' };

const run = (overrides: Partial<Parameters<typeof runBatchAutoLabel>[0]> = {}) => {
    const save = vi.fn().mockResolvedValue(undefined);
    const onProgress = vi.fn();
    const result = runBatchAutoLabel({
        sampleIds: ['a'],
        detect: vi.fn().mockResolvedValue([person, car]),
        save,
        classNames: new Set(['person', 'car']),
        signal: new AbortController().signal,
        onProgress,
        ...overrides
    });
    return { result, save, onProgress };
};

describe('runBatchAutoLabel', () => {
    it('saves only ticked classes', async () => {
        const { result, save } = run({ classNames: new Set(['person']) });

        expect(await result).toEqual({ done: 1, annotationCount: 1, failedSampleIds: [] });
        expect(save).toHaveBeenCalledWith('a', [person]);
    });

    it('skips saving an image with nothing kept but counts it done', async () => {
        const { result, save } = run({ classNames: new Set(['dog']) });

        expect(await result).toEqual({ done: 1, annotationCount: 0, failedSampleIds: [] });
        expect(save).not.toHaveBeenCalled();
    });

    it('records a failed image and continues', async () => {
        const detect = vi.fn(async (sampleId: string) => {
            if (sampleId === 'b') throw new Error('Image not found');
            return [person];
        });

        const { result, save } = run({ sampleIds: ['a', 'b', 'c'], detect });

        expect(await result).toEqual({ done: 3, annotationCount: 2, failedSampleIds: ['b'] });
        expect(save).toHaveBeenCalledTimes(2);
    });

    it('stops after the current image on abort', async () => {
        const controller = new AbortController();

        const { result, save } = run({
            sampleIds: ['a', 'b', 'c'],
            signal: controller.signal,
            onProgress: () => controller.abort()
        });

        expect((await result).done).toBe(1);
        expect(save).toHaveBeenCalledOnce();
    });

    it('reports the progress after each image', async () => {
        const { result, onProgress } = run({ sampleIds: ['a', 'b'] });
        await result;

        expect(onProgress.mock.calls).toEqual([
            [{ done: 1, annotationCount: 2, failedCount: 0 }],
            [{ done: 2, annotationCount: 4, failedCount: 0 }]
        ]);
    });
});
