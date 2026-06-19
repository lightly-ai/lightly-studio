import { describe, expect, it } from 'vitest';
import { resolveEffectiveColorBySource } from './resolveEffectiveColorBySource';

describe('resolveEffectiveColorBySource', () => {
    describe('when enforceColoringByClass is disabled', () => {
        it('returns true when source coloring is active', () => {
            expect(resolveEffectiveColorBySource(true, false)).toBe(true);
        });

        it('returns false when source coloring is inactive', () => {
            expect(resolveEffectiveColorBySource(false, false)).toBe(false);
        });
    });

    describe('when enforceColoringByClass is enabled', () => {
        it('returns false even when source coloring is active', () => {
            expect(resolveEffectiveColorBySource(true, true)).toBe(false);
        });

        it('returns false when source coloring is inactive', () => {
            expect(resolveEffectiveColorBySource(false, true)).toBe(false);
        });
    });
});
