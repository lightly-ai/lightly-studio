import { describe, expect, it } from 'vitest';
import { isFieldExpanded, matchesFieldSearch } from './metadataFieldList';

describe('matchesFieldSearch', () => {
    it('ignores case and surrounding spaces', () => {
        expect(matchesFieldSearch('Location_Type', ' location ')).toBe(true);
        expect(matchesFieldSearch('split', 'loc')).toBe(false);
    });
});

describe('isFieldExpanded', () => {
    it('starts open with 8 fields and collapsed with 9', () => {
        expect(isFieldExpanded({}, 'split', 8)).toBe(true);
        expect(isFieldExpanded({}, 'split', 9)).toBe(false);
    });

    it('keeps the state the user picked', () => {
        expect(isFieldExpanded({ split: true }, 'split', 9)).toBe(true);
        expect(isFieldExpanded({ split: false }, 'split', 2)).toBe(false);
    });
});
