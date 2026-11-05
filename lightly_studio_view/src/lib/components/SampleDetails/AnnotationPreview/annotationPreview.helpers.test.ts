import { describe, expect, it } from 'vitest';
import { pickClassName } from './annotationPreview.helpers';

describe('annotationPreview.helpers', () => {
    it('picks the selected annotation class name as is', () => {
        expect(pickClassName({ selected: ' car ', hint: 'dog' })).toBe(' car ');
        expect(pickClassName({ selected: '', hint: 'dog' })).toBe('');
    });

    it('picks the trimmed hint or the fallback without a selected class', () => {
        expect(pickClassName({ selected: null, hint: ' dog ' })).toBe('dog');
        expect(pickClassName({ selected: undefined, hint: '  ' })).toBe('object');
    });
});
