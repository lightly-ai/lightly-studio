import { describe, expect, it } from 'vitest';
import { isValidSuffix } from './sceneUpdateFileOptions';

describe('isValidSuffix', () => {
    it.each(['', '_labeled', 'v1.2-final'])('accepts %s', (suffix) => {
        expect(isValidSuffix(suffix)).toBe(true);
    });

    it.each(['_x/y', '_x\\y', '_x y'])('rejects %j', (suffix) => {
        expect(isValidSuffix(suffix)).toBe(false);
    });
});
