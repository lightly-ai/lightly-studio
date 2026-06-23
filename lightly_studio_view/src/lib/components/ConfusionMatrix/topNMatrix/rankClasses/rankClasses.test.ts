import { describe, expect, it } from 'vitest';
import { getRealClasses } from '../getRealClasses/getRealClasses';
import { rankClasses } from './rankClasses';
import { small3Classes } from '../../fixtures';

describe('rankClasses', () => {
    it('most-confused matches the confusion ranking and least-confused reverses it', () => {
        expect(rankClasses(small3Classes, 'most-confused')).toEqual(['person', 'car', 'bike']);
        expect(rankClasses(small3Classes, 'least-confused')).toEqual(['bike', 'car', 'person']);
    });

    it('most-samples ranks by ground-truth row totals', () => {
        expect(rankClasses(small3Classes, 'most-samples')).toEqual(['person', 'car', 'bike']);
    });

    it('alphabetical sorts labels without mutating the source order', () => {
        expect(rankClasses(small3Classes, 'alphabetical')).toEqual(['bike', 'car', 'person']);
        expect(getRealClasses(small3Classes)).toEqual(['bike', 'car', 'person']);
    });
});
