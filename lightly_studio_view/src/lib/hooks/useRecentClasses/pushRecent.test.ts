import { describe, expect, it } from 'vitest';
import { pushRecent } from './pushRecent';

describe('pushRecent', () => {
    it('moves a known class to the front', () => {
        expect(pushRecent(['a', 'b', 'c', 'd', 'e'], 'c')).toEqual(['c', 'a', 'b', 'd', 'e']);
    });

    it('drops the oldest class past the limit', () => {
        expect(pushRecent(['a', 'b', 'c', 'd', 'e'], 'f')).toEqual(['f', 'a', 'b', 'c', 'd']);
    });

    it('ignores a blank name', () => {
        expect(pushRecent(['a'], '  ')).toEqual(['a']);
    });
});
