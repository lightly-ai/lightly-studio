import { describe, expect, it } from 'vitest';
import { formatTranslationErrors } from './QueryEditor.helpers';

describe('formatTranslationErrors', () => {
    it('adds the position when it is known and joins errors with newlines', () => {
        const result = formatTranslationErrors({
            status: 'error',
            errors: [
                { message: 'unexpected token', line: 2, column: 7 },
                { message: 'Unsupported comparison' }
            ]
        });

        expect(result).toBe('unexpected token (line 2, column 7)\nUnsupported comparison');
    });
});
