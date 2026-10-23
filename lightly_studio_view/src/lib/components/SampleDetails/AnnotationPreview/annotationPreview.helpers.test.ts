import { describe, expect, it } from 'vitest';
import { getAnnotationPreviewErrorMessage, pickClassName } from './annotationPreview.helpers';

describe('annotationPreview.helpers', () => {
    it('picks the selected annotation class name as is', () => {
        expect(pickClassName({ selected: ' car ', hint: 'dog' })).toBe(' car ');
        expect(pickClassName({ selected: '', hint: 'dog' })).toBe('');
    });

    it('picks the trimmed hint or the fallback without a selected class', () => {
        expect(pickClassName({ selected: null, hint: ' dog ' })).toBe('dog');
        expect(pickClassName({ selected: undefined, hint: '  ' })).toBe('object');
    });

    it('reads the error message from the response body', () => {
        expect(getAnnotationPreviewErrorMessage({ error: 'Provider unavailable' })).toBe(
            'Provider unavailable'
        );
        expect(getAnnotationPreviewErrorMessage({ detail: 'Bad request' })).toBe('Bad request');
        expect(getAnnotationPreviewErrorMessage(new Error('boom'))).toBe('boom');
        expect(getAnnotationPreviewErrorMessage(undefined)).toBe('Unknown error');
    });

    it('reads the first message of a validation error', () => {
        expect(
            getAnnotationPreviewErrorMessage({
                detail: [{ loc: ['body', 'prompt'], msg: 'Field required', type: 'missing' }]
            })
        ).toBe('Field required');
    });
});
