import { describe, expect, it } from 'vitest';
import { getAnnotationPreviewErrorMessage, pickClassName } from './annotationPreview.helpers';

describe('annotationPreview.helpers', () => {
    it('picks the first non-blank annotation class name', () => {
        expect(pickClassName([null, '  ', ' car ', 'dog'])).toBe('car');
        expect(pickClassName([undefined, ''])).toBe('object');
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
