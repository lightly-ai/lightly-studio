import { expect, it } from 'vitest';
import { getQuotedMetricRange } from './getQuotedMetricRange';

it.each([
    'sample_evaluation(name = "tp"',
    'sample_evaluation(name = "run# AND" "tp"',
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

it.each(['AND', 'OR', 'NOT', '(', 'AND NOT ('])('handles comments after %s', (operator) => {
    const prefix = `sample_evaluation(name = "run#1" ${operator} # explanation "ignored"\n  `;
    expect(
        getQuotedMetricRange({
            text: `${prefix}"tp" > 0)`,
            offset: prefix.length + 3,
            position: { lineNumber: 2, column: 6 }
        })
    ).toEqual({ startLineNumber: 2, endLineNumber: 2, startColumn: 3, endColumn: 7 });
});
