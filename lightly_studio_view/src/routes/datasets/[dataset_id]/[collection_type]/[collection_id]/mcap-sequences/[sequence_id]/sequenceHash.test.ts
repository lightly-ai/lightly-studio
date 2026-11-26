import { describe, expect, it } from 'vitest';
import { buildSequenceHash, getCameraFromHash, getTickNumberFromHash } from './sequenceHash';

describe('getTickNumberFromHash', () => {
    it.each([
        ['#tick=4', 4],
        ['', 1],
        ['#tick=0', 1],
        ['#tick=-2', 1],
        ['#other=4', 1],
        ['#tick=abc', 1],
        ['#tick=1.5', 1]
    ])('returns %s as tick number %i', (hash, expected) => {
        expect(getTickNumberFromHash(hash)).toBe(expected);
    });
});

describe('getCameraFromHash', () => {
    it('reads the camera next to the tick', () => {
        expect(getCameraFromHash('#tick=3&camera=CAM_FRONT')).toBe('CAM_FRONT');
    });

    it.each([['#tick=3'], ['#camera='], ['']])('returns undefined for %j', (hash) => {
        expect(getCameraFromHash(hash)).toBeUndefined();
    });

    it('round trips a name with a slash and a space', () => {
        const hash = `#${buildSequenceHash({ tick: 2, camera: '/cam/front left' })}`;
        expect(getCameraFromHash(hash)).toBe('/cam/front left');
    });
});

describe('buildSequenceHash', () => {
    it('contains only the tick without a camera', () => {
        expect(buildSequenceHash({ tick: 4 })).toBe('tick=4');
    });

    it('appends the encoded camera', () => {
        expect(buildSequenceHash({ tick: 4, camera: 'CAM_B' })).toBe('tick=4&camera=CAM_B');
    });
});
