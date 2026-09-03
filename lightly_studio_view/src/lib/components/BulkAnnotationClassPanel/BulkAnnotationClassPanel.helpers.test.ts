import { describe, expect, it } from 'vitest';
import { summarizeApply, withSelectedOption } from './BulkAnnotationClassPanel.helpers';

describe('summarizeApply', () => {
    const selectionClassCounts = [
        { className: 'dog', sampleCount: 3 },
        { className: 'cat', sampleCount: 1 }
    ];

    it('skips the images that already have the annotation class', () => {
        expect(
            summarizeApply({ className: 'dog', selectedCount: 10, selectionClassCounts })
        ).toEqual({ skippedCount: 3, affectedCount: 7 });
    });

    it('skips nothing for a class that is not in the selection', () => {
        expect(
            summarizeApply({ className: 'horse', selectedCount: 10, selectionClassCounts })
        ).toEqual({ skippedCount: 0, affectedCount: 10 });
    });

    it('clamps a count larger than the selection so affectedCount stays non-negative', () => {
        expect(
            summarizeApply({ className: 'dog', selectedCount: 2, selectionClassCounts })
        ).toEqual({ skippedCount: 2, affectedCount: 0 });
    });
});

describe('withSelectedOption', () => {
    it('appends a selected name that is not in the options', () => {
        expect(withSelectedOption(['dog'], 'cat')).toEqual(['dog', 'cat']);
    });

    it('keeps the options unchanged for a known or empty selection', () => {
        expect(withSelectedOption(['dog'], 'dog')).toEqual(['dog']);
        expect(withSelectedOption(['dog'], '')).toEqual(['dog']);
    });
});
