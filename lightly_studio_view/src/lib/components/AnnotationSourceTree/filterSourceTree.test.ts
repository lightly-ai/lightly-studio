import { describe, expect, it } from 'vitest';
import { splitMatch } from './filterSourceTree';

describe('splitMatch', () => {
    it('splits around the first match', () => {
        expect(splitMatch('Raccoon', 'cco')).toEqual({ before: 'Ra', match: 'cco', after: 'on' });
        expect(splitMatch('Raccoon', 'x')).toEqual({ before: 'Raccoon', match: '', after: '' });
    });
});
