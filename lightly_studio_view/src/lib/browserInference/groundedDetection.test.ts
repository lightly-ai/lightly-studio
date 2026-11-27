import { describe, expect, it } from 'vitest';
import { decodeGroundedDetections, toPhraseSpans } from './groundedDetection';

const CLS = 101;
const SEP = 102;
const DOT = 1012;
const tokens = { specialIds: new Set([CLS, SEP]), separatorId: DOT };

// A logit whose sigmoid is the given probability.
const logit = (probability: number) => Math.log(probability / (1 - probability));

describe('toPhraseSpans', () => {
    it('returns the token range of each phrase between the separators', () => {
        // "[CLS] fork lift . pallet . [SEP]"
        const spans = toPhraseSpans([CLS, 5, 6, DOT, 7, DOT, SEP], tokens);

        expect(spans).toEqual([
            { start: 1, end: 3 },
            { start: 4, end: 5 }
        ]);
    });

    it('keeps a last phrase without a separator', () => {
        expect(toPhraseSpans([CLS, 5, SEP], tokens)).toEqual([{ start: 1, end: 2 }]);
    });
});

describe('decodeGroundedDetections', () => {
    const numTokens = 4;
    const spans = [
        { start: 1, end: 3 },
        { start: 3, end: 4 }
    ];
    const params = {
        numTokens,
        spans,
        classNames: ['forklift', 'pallet'],
        imageWidth: 200,
        imageHeight: 100,
        threshold: 0.3
    };

    it('labels each query with the phrase of its best token and scales the box', () => {
        const logits = new Float32Array([
            // Query 0: the second token of "forklift" is the best.
            logit(0.1),
            logit(0.2),
            logit(0.9),
            logit(0.4),
            // Query 1: "pallet" is the best.
            logit(0.1),
            logit(0.1),
            logit(0.2),
            logit(0.6)
        ]);
        const boxes = new Float32Array([0.5, 0.5, 0.2, 0.4, 0.25, 0.25, 0.1, 0.1]);

        const previews = decodeGroundedDetections({ ...params, logits, boxes });

        expect(previews).toHaveLength(2);
        expect(previews[0]).toMatchObject({
            class_name: 'forklift',
            bbox: { x: 80, y: 30, width: 40, height: 40 },
            segmentation_mask: null
        });
        expect(previews[0].score).toBeCloseTo(0.9);
        expect(previews[1].class_name).toBe('pallet');
        expect(previews[1].score).toBeCloseTo(0.6);
    });

    it('drops queries at or below the threshold and ignores tokens outside the phrases', () => {
        const logits = new Float32Array([
            // Only the CLS token scores high.
            logit(0.99),
            logit(0.29),
            logit(0.1),
            logit(0.1)
        ]);
        const boxes = new Float32Array([0.5, 0.5, 0.2, 0.2]);

        expect(decodeGroundedDetections({ ...params, logits, boxes })).toEqual([]);
    });

    it('sorts the previews by score, best first', () => {
        const logits = new Float32Array([
            logit(0.1),
            logit(0.5),
            logit(0.1),
            logit(0.1),
            logit(0.1),
            logit(0.1),
            logit(0.1),
            logit(0.8)
        ]);
        const boxes = new Float32Array(8).fill(0.5);

        const scores = decodeGroundedDetections({ ...params, logits, boxes }).map(
            (preview) => preview.class_name
        );

        expect(scores).toEqual(['pallet', 'forklift']);
    });
});
