import { describe, expect, it } from 'vitest';
import { formatBulkCreateToast, shouldBulkCreateByFilter } from './useBulkCreateClassifications';

const filter = { filter_type: 'image' as const };

describe('shouldBulkCreateByFilter', () => {
    it('uses the filter route only for an intact select-all snapshot', () => {
        expect(
            shouldBulkCreateByFilter({
                selectAllSnapshot: { filter, size: 2 },
                selectedIds: new Set(['a', 'b'])
            })
        ).toBe(true);

        expect(
            shouldBulkCreateByFilter({
                selectAllSnapshot: { filter, size: 3 },
                selectedIds: new Set(['a', 'b'])
            })
        ).toBe(false);

        expect(
            shouldBulkCreateByFilter({
                selectAllSnapshot: null,
                selectedIds: new Set(['a', 'b'])
            })
        ).toBe(false);
    });
});

describe('formatBulkCreateToast', () => {
    it('formats created and skipped outcomes', () => {
        expect(
            formatBulkCreateToast(
                { created_annotation_ids: ['a'], created_count: 40, skipped_count: 0 },
                40
            )
        ).toBe('Added the class to 40 images.');
        expect(
            formatBulkCreateToast(
                { created_annotation_ids: ['a'], created_count: 28, skipped_count: 12 },
                40
            )
        ).toBe('Added to 28 of 40 images; 12 already had this class.');
        expect(
            formatBulkCreateToast(
                { created_annotation_ids: [], created_count: 0, skipped_count: 5 },
                5
            )
        ).toBe('No images changed; all 5 already had this class.');
    });
});
