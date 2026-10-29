import { describe, expect, it } from 'vitest';
import { describeExportScope } from './describeExportScope';

describe('describeExportScope', () => {
    it('states the count and hints at tag filtering when no tag filter is active', () => {
        expect(describeExportScope({ count: 120, sampleType: 'image', tagNames: [] })).toEqual({
            summary: 'Exports the 120 images matching your current filters.',
            hint: 'To export one tag, filter by that tag first.'
        });
    });

    it('names the tag and drops the hint when one tag is filtered', () => {
        expect(
            describeExportScope({ count: 1, sampleType: 'image', tagNames: ['to_label'] })
        ).toEqual({
            summary: 'Exports the 1 image matching your current filters in tag to_label.',
            hint: undefined
        });
    });

    it('names all filtered tags', () => {
        const { summary } = describeExportScope({
            count: 5,
            sampleType: 'video',
            tagNames: ['train', 'val']
        });
        expect(summary).toBe(
            'Exports the 5 videos matching your current filters in tags train or val.'
        );
    });

    it('falls back to samples for other sample types', () => {
        const { summary } = describeExportScope({
            count: 2,
            sampleType: 'video_frame',
            tagNames: []
        });
        expect(summary).toBe('Exports the 2 samples matching your current filters.');
    });
});
