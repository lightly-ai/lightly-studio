import { describe, expect, it } from 'vitest';
import { MANY_FIELDS, matchesFieldSearch } from './metadataFieldList';

describe('matchesFieldSearch', () => {
    it('ignores case and surrounding spaces', () => {
        expect(matchesFieldSearch('Location_Type', ' location ')).toBe(true);
        expect(matchesFieldSearch('split', 'loc')).toBe(false);
    });
});

describe('MANY_FIELDS', () => {
    it('shows the field search only above 8 fields', () => {
        expect(MANY_FIELDS).toBe(8);
    });
});
