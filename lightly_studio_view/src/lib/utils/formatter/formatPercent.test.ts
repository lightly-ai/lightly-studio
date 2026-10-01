import { describe, expect, it } from 'vitest';
import { formatPercent } from './formatPercent';

describe('formatPercent', () => {
    it('formats a ratio as a percentage with one decimal', () => {
        expect(formatPercent(0.25)).toBe('25.0%');
    });

    it('renders tiny non-zero shares as <0.1%', () => {
        expect(formatPercent(0.0001)).toBe('<0.1%');
    });

    it('formats zero as 0.0%', () => {
        expect(formatPercent(0)).toBe('0.0%');
    });
});
