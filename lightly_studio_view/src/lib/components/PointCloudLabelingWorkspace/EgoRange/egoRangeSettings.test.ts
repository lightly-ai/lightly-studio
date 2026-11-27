import { describe, expect, it } from 'vitest';
import {
    DEFAULT_EGO_RANGE_SETTINGS,
    resolveEgoFrame,
    sanitizeEgoRangeSettings
} from './egoRangeSettings';

describe('sanitizeEgoRangeSettings', () => {
    it('returns the defaults for a missing value', () => {
        expect(sanitizeEgoRangeSettings(undefined)).toEqual({
            enabled: false,
            radius: 40,
            egoFrameByDataset: {}
        });
    });

    it('clamps the radius to 1 and 500 m', () => {
        expect(sanitizeEgoRangeSettings({ radius: -5 }).radius).toBe(1);
        expect(sanitizeEgoRangeSettings({ radius: 9000 }).radius).toBe(500);
    });

    it('replaces values of the wrong type with the defaults', () => {
        const settings = sanitizeEgoRangeSettings({ radius: 'abc', enabled: 'yes' });

        expect(settings.radius).toBe(DEFAULT_EGO_RANGE_SETTINGS.radius);
        expect(settings.enabled).toBe(DEFAULT_EGO_RANGE_SETTINGS.enabled);
    });

    it('keeps only the ego frames that are strings', () => {
        const settings = sanitizeEgoRangeSettings({
            egoFrameByDataset: { a: 'CABIN', b: 3 }
        });

        expect(settings.egoFrameByDataset).toEqual({ a: 'CABIN' });
    });
});

describe('resolveEgoFrame', () => {
    it('keeps the stored frame when the sequence has it', () => {
        expect(resolveEgoFrame('base', ['map', 'base'])).toBe('base');
    });

    it('ignores a stored frame that the sequence does not have', () => {
        expect(resolveEgoFrame('CABIN', ['map', 'base_link'])).toBe('base_link');
    });

    it('prefers CABIN over base_link', () => {
        expect(resolveEgoFrame(undefined, ['map', 'CABIN', 'base_link'])).toBe('CABIN');
    });

    it('returns null without an ego frame', () => {
        expect(resolveEgoFrame(undefined, ['map', 'odom'])).toBeNull();
    });
});
