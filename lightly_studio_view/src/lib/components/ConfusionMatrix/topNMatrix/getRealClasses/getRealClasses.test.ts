import { describe, expect, it } from 'vitest';
import { getRealClasses } from './getRealClasses';
import { small3Classes } from '../../fixtures';

describe('getRealClasses', () => {
    it('excludes sentinel labels', () => {
        expect(getRealClasses(small3Classes)).toEqual(['bike', 'car', 'person']);
    });
});
