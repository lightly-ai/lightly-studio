import { describe, expect, it } from 'vitest';
import { rankClassesByConfusion } from './rankClassesByConfusion';
import { small3Classes } from '../../fixtures';

describe('rankClassesByConfusion', () => {
    it('ranks classes by off-diagonal involvement, descending', () => {
        // person=44, car=22, bike=13
        expect(rankClassesByConfusion(small3Classes)).toEqual(['person', 'car', 'bike']);
    });
});
