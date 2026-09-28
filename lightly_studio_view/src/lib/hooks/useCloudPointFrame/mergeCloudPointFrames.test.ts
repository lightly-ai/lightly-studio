import { describe, expect, it } from 'vitest';
import { mergeCloudPointFrames } from './mergeCloudPointFrames';
import type { CloudPointFrame } from './types';

function makeFrame(overrides: Partial<CloudPointFrame> = {}): CloudPointFrame {
    return {
        batch: {
            positions: new Float32Array([1, 2, 3]),
            intensities: new Float32Array([0.5]),
            colors: new Float32Array([0.1, 0.2, 0.3]),
            count: 1
        },
        channelId: 1,
        timestampNs: '100',
        frameId: 'a',
        sourcePointCount: 1,
        bounds: { min: [1, 2, 3], max: [1, 2, 3] },
        channels: [{ channelId: 1, timestampNs: '100', frameId: 'a' }],
        ...overrides
    };
}

describe('mergeCloudPointFrames', () => {
    it('concatenates positions, intensities, and colors', () => {
        const first = makeFrame();
        const second = makeFrame({
            batch: {
                positions: new Float32Array([4, 5, 6]),
                intensities: new Float32Array([0.75]),
                colors: new Float32Array([0.4, 0.5, 0.6]),
                count: 1
            }
        });

        const result = mergeCloudPointFrames([first, second]);

        expect(result.batch).toEqual({
            positions: new Float32Array([1, 2, 3, 4, 5, 6]),
            intensities: new Float32Array([0.5, 0.75]),
            colors: new Float32Array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]),
            count: 2
        });
    });

    it('copies only the active points of padded batches', () => {
        const padded = makeFrame({
            batch: {
                positions: new Float32Array([1, 2, 3, 0, 0, 0]),
                intensities: new Float32Array([0.5, 0]),
                colors: new Float32Array([0.1, 0.2, 0.3, 0, 0, 0]),
                count: 1
            }
        });

        const result = mergeCloudPointFrames([padded]);

        expect(result.batch).toEqual({
            positions: new Float32Array([1, 2, 3]),
            intensities: new Float32Array([0.5]),
            colors: new Float32Array([0.1, 0.2, 0.3]),
            count: 1
        });
    });

    it('drops colors when any frame lacks them', () => {
        const withColors = makeFrame();
        const withoutColors = makeFrame({
            batch: {
                positions: new Float32Array([4, 5, 6]),
                intensities: new Float32Array([0.75]),
                count: 1
            }
        });

        const result = mergeCloudPointFrames([withColors, withoutColors]);

        expect(result.batch.colors).toBeUndefined();
        expect(result.batch.count).toBe(2);
    });

    it('merges bounds, sums source points, and joins frame ids', () => {
        const first = makeFrame({
            frameId: 'a',
            sourcePointCount: 3,
            bounds: { min: [0, 0, 0], max: [2, 2, 2] },
            channels: [{ channelId: 1, timestampNs: '100', frameId: 'a' }]
        });
        const second = makeFrame({
            frameId: 'b',
            sourcePointCount: 4,
            bounds: { min: [-1, 1, 1], max: [5, 3, 1] },
            channels: [{ channelId: 2, timestampNs: '200', frameId: 'b' }]
        });

        const result = mergeCloudPointFrames([first, second]);

        expect(result.frameId).toBe('a,b');
        expect(result.sourcePointCount).toBe(7);
        expect(result.bounds).toEqual({ min: [-1, 0, 0], max: [5, 3, 2] });
        expect(result.channels).toEqual([
            { channelId: 1, timestampNs: '100', frameId: 'a' },
            { channelId: 2, timestampNs: '200', frameId: 'b' }
        ]);
    });

    it('takes channel id and timestamp from the first frame', () => {
        const first = makeFrame({ channelId: 9, timestampNs: '111' });
        const second = makeFrame({ channelId: 3, timestampNs: '222' });

        const result = mergeCloudPointFrames([first, second]);

        expect(result.channelId).toBe(9);
        expect(result.timestampNs).toBe('111');
    });
});
