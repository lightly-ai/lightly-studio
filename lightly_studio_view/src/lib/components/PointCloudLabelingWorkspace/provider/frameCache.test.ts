import { describe, expect, it } from 'vitest';
import { canonicalCoordinateFrame, createPointCloudFrame } from '../domain';
import { FrameCache } from './frameCache';

function frame() {
    return createPointCloudFrame({
        id: 'f',
        source: { recordingId: 'r', streamId: 's', messageId: 'm', publishedAt: null },
        timestamp: { nanoseconds: '1', clockId: 'r' },
        coordinateFrame: canonicalCoordinateFrame('sensor'),
        sourcePointCount: 1,
        positions: new Float32Array([1, 2, 3]),
        cameras: []
    });
}

describe('FrameCache', () => {
    it('evicts least recently used frames within the byte limit', () => {
        const cache = new FrameCache(24);
        const value = frame();
        cache.set('a', value);
        cache.set('b', value);
        cache.get('a');
        cache.set('c', value);
        expect(cache.get('b')).toBeUndefined();
        expect(cache.get('a')).toBe(value);
        expect(cache.bytes).toBe(24);
        cache.clear();
        expect(cache.bytes).toBe(0);
    });

    it('rejects limits that are not non-negative integers', () => {
        expect(() => new FrameCache(-1)).toThrow(/non-negative integers/);
        expect(() => new FrameCache(1.5)).toThrow(/non-negative integers/);
        expect(() => new FrameCache(100, -1)).toThrow(/non-negative integers/);
    });

    it('does not cache oversized frames and bounds entry count', () => {
        const small = new FrameCache(4);
        small.set('a', frame());
        expect(small.get('a')).toBeUndefined();
        const cache = new FrameCache(100, 1);
        cache.set('a', frame());
        cache.set('b', frame());
        expect(cache.get('a')).toBeUndefined();
        expect(cache.bytes).toBe(12);
    });
});
