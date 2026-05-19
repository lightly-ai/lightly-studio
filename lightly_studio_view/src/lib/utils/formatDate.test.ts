import { describe, expect, it } from 'vitest';
import { formatDate } from './formatDate';

describe('formatDate', () => {
    it('formats a date with year, short month, day, hour and minute', () => {
        const expected = new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date('2026-01-15T10:30:00Z'));

        expect(formatDate(new Date('2026-01-15T10:30:00Z'))).toBe(expected);
    });
});
