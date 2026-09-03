import { describe, expect, it } from 'vitest';
import { withSelectedOption } from './BulkAnnotationClassPanel.helpers';

describe('withSelectedOption', () => {
    it('appends a selected name that is not in the options', () => {
        expect(withSelectedOption(['dog'], 'cat')).toEqual(['dog', 'cat']);
    });

    it('keeps the options unchanged for a known or empty selection', () => {
        expect(withSelectedOption(['dog'], 'dog')).toEqual(['dog']);
        expect(withSelectedOption(['dog'], '')).toEqual(['dog']);
    });
});
