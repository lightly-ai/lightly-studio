import { describe, expect, it } from 'vitest';
import { formatDuration, latestReasoningHeading, toPlainReasoning } from './agentProgress';

describe('latestReasoningHeading', () => {
    it('gets the newest bold heading line', () => {
        const text =
            '**Checking classes**\n\nThe user wants dogs.\n\n**Planning the selection**\n\nI';
        expect(latestReasoningHeading(text)).toBe('Planning the selection');
    });

    it('gets nothing for text without a heading line', () => {
        expect(latestReasoningHeading('The user wants **20** images.')).toBeUndefined();
        expect(latestReasoningHeading('')).toBeUndefined();
    });
});

describe('toPlainReasoning', () => {
    it('removes the bold markers', () => {
        expect(toPlainReasoning('**Planning**\n\nUse **diversity**.\n')).toBe(
            'Planning\n\nUse diversity.'
        );
    });
});

describe('formatDuration', () => {
    it('formats seconds and minutes', () => {
        expect(formatDuration(0)).toBe('0s');
        expect(formatDuration(7_400)).toBe('7s');
        expect(formatDuration(65_000)).toBe('1m 05s');
    });
});
