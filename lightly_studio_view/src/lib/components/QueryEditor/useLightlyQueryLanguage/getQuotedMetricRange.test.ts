import { describe, expect, it } from 'vitest';
import { getQuotedMetricRange } from './getQuotedMetricRange';

describe('getQuotedMetricRange', () => {
    it.each([
        'sample_evaluation(name = "tp"',
        'sample_evaluation(name = "run1" AND "tp" > 0 ',
        'sample_evaluation(name = "run1" AND # "tp"'
    ])('keeps ordinary completion ranges for %s', (text) => {
        expect(
            getQuotedMetricRange({
                text,
                offset: text.length,
                position: { lineNumber: 1, column: text.length + 1 }
            })
        ).toBeUndefined();
    });

    it('replaces a metric on a later line after nested negation', () => {
        const prefix = 'sample_evaluation(name = "run1" AND\n  NOT (';
        const text = `${prefix}'tp' > 0))`;
        expect(
            getQuotedMetricRange({
                text,
                offset: prefix.length + 4,
                position: { lineNumber: 2, column: 12 }
            })
        ).toEqual({ startLineNumber: 2, endLineNumber: 2, startColumn: 8, endColumn: 12 });
    });
});
