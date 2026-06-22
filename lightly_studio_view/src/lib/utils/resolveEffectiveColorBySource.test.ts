import { describe, expect, it } from 'vitest';
import { resolveEffectiveColorBySource } from './resolveEffectiveColorBySource';

describe('resolveEffectiveColorBySource', () => {
    it('returns true when multiple sources are visible and enforce is disabled', () => {
        expect(
            resolveEffectiveColorBySource({
                multipleSourcesVisible: true,
                enforceColoringByClass: false
            })
        ).toBe(true);
    });

    it('returns false when only one source is visible and enforce is disabled', () => {
        expect(
            resolveEffectiveColorBySource({
                multipleSourcesVisible: false,
                enforceColoringByClass: false
            })
        ).toBe(false);
    });

    it('returns false when enforce is enabled and multiple sources are visible', () => {
        expect(
            resolveEffectiveColorBySource({
                multipleSourcesVisible: true,
                enforceColoringByClass: true
            })
        ).toBe(false);
    });

    it('returns false when enforce is enabled and only one source is visible', () => {
        expect(
            resolveEffectiveColorBySource({
                multipleSourcesVisible: false,
                enforceColoringByClass: true
            })
        ).toBe(false);
    });
});
