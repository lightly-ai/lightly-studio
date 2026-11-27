import { describe, expect, it } from 'vitest';
import { decodeDetections, toInputTensor } from './detection';

describe('toInputTensor', () => {
    it('converts RGBA to normalized CHW and ignores alpha', () => {
        const rgba = new Uint8ClampedArray([255, 0, 0, 255, 0, 255, 0, 0]);

        const tensor = toInputTensor({
            rgba,
            width: 2,
            height: 1,
            normalize: { mean: [0.5, 0.5, 0.5], std: [0.5, 0.5, 0.5] }
        });

        expect(Array.from(tensor)).toEqual([1, -1, -1, 1, -1, -1]);
    });

    it('only scales to [0, 1] without normalization', () => {
        const rgba = new Uint8ClampedArray([255, 0, 51, 255]);

        const tensor = toInputTensor({ rgba, width: 1, height: 1, normalize: null });

        const [red, green, blue] = Array.from(tensor);
        expect([red, green]).toEqual([1, 0]);
        expect(blue).toBeCloseTo(0.2, 6);
    });
});

describe('decodeDetections', () => {
    // Query 0 is a person, query 1 is a car with a score of exactly 0.5.
    const params = {
        logits: new Float32Array([2, -5, -5, 0]),
        boxes: new Float32Array([0.5, 0.5, 0.5, 0.5, 0.25, 0.25, 0.1, 0.1]),
        numClasses: 2,
        classNames: ['person', 'car'],
        imageWidth: 200,
        imageHeight: 100,
        topK: 300
    };

    it('keeps scores strictly above the threshold, in pixel xywh', () => {
        const [only, ...rest] = decodeDetections({ ...params, threshold: 0.6 });

        expect(rest).toEqual([]);
        expect(only).toMatchObject({
            class_name: 'person',
            bbox: { x: 50, y: 25, width: 100, height: 50 },
            segmentation_mask: null
        });
        expect(only.score).toBeCloseTo(0.8808, 4);
        expect(decodeDetections({ ...params, threshold: 0.5 })).toHaveLength(1);
    });

    it('returns lower-scored objects for a lower threshold', () => {
        const detections = decodeDetections({ ...params, threshold: 0.4 });

        expect(detections).toHaveLength(2);
        expect(detections[1]).toMatchObject({
            class_name: 'car',
            bbox: { x: 40, y: 20, width: 20, height: 10 }
        });
    });

    it('keeps only the top k scores', () => {
        expect(decodeDetections({ ...params, threshold: 0, topK: 1 })).toHaveLength(1);
    });
});
