import { describe, expect, it } from 'vitest';
import { getAnnotationPreviewErrorMessage, pickClassName } from './annotationPreview.helpers';
import { ApiError } from '$lib/api/ApiError';

describe('annotationPreview.helpers', () => {
    it('picks the selected annotation class name as is', () => {
        expect(pickClassName({ selected: ' car ', hint: 'dog' })).toBe(' car ');
        expect(pickClassName({ selected: '', hint: 'dog' })).toBe('');
    });

    it('picks the trimmed hint or the fallback without a selected class', () => {
        expect(pickClassName({ selected: null, hint: ' dog ' })).toBe('dog');
        expect(pickClassName({ selected: undefined, hint: '  ' })).toBe('object');
    });

    it('reads the error message', () => {
        expect(getAnnotationPreviewErrorMessage(new ApiError('Provider unavailable', 503))).toBe(
            'Provider unavailable'
        );
        expect(getAnnotationPreviewErrorMessage(new Error('boom'))).toBe('boom');
        expect(getAnnotationPreviewErrorMessage(undefined)).toBe('Unknown error');
    });
});
