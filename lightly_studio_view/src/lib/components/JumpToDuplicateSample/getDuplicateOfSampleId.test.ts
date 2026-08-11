import { describe, expect, it } from 'vitest';
import { getDuplicateOfSampleId } from './getDuplicateOfSampleId';

describe('getDuplicateOfSampleId', () => {
    it('returns the duplicate_of sample id when present', () => {
        expect(
            getDuplicateOfSampleId({
                data: { duplicate_of: 'kept-sample-id' }
            })
        ).toBe('kept-sample-id');
    });

    it('returns null when metadata is missing or invalid', () => {
        expect(getDuplicateOfSampleId(null)).toBeNull();
        expect(getDuplicateOfSampleId({})).toBeNull();
        expect(getDuplicateOfSampleId({ data: {} })).toBeNull();
        expect(getDuplicateOfSampleId({ data: { duplicate_of: '' } })).toBeNull();
        expect(getDuplicateOfSampleId({ data: { duplicate_of: 123 } })).toBeNull();
    });
});
