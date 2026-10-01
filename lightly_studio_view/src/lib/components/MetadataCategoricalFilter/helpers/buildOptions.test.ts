import { describe, expect, it } from 'vitest';
import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
import { buildOptions } from './buildOptions';

const value = (id: string, v: string, count = 1): CategoricalMetadataBucket => ({
    id,
    kind: 'value',
    value: v,
    label: v,
    count
});
const missing = (count = 1): CategoricalMetadataBucket => ({
    id: 'missing',
    kind: 'missing',
    value: null,
    label: 'Missing',
    count
});
const other = (): CategoricalMetadataBucket => ({
    id: 'other',
    kind: 'other',
    label: 'Other',
    count: 5
});

describe('buildOptions', () => {
    it('returns empty array when buckets and selectedValues are empty', () => {
        expect(buildOptions([], [])).toEqual([]);
    });

    it('maps selectable buckets to non-retained options preserving order', () => {
        const buckets = [value('a', 'foo', 3), missing(2)];
        const result = buildOptions(buckets, []);
        expect(result).toHaveLength(2);
        expect(result[0]).toEqual({ bucket: buckets[0], retained: false });
        expect(result[1]).toEqual({ bucket: buckets[1], retained: false });
    });

    it('excludes other buckets from options', () => {
        const result = buildOptions([value('a', 'foo'), other()], []);
        expect(result).toHaveLength(1);
        expect(result[0].bucket.kind).toBe('value');
    });

    it('appends a retained option for a string selected value absent from buckets', () => {
        const result = buildOptions([], ['stale']);
        expect(result).toHaveLength(1);
        expect(result[0]).toMatchObject({
            retained: true,
            bucket: { kind: 'value', value: 'stale', count: 0 }
        });
    });

    it('appends a retained missing option for null selected value absent from buckets', () => {
        const result = buildOptions([], [null]);
        expect(result).toHaveLength(1);
        expect(result[0]).toMatchObject({
            retained: true,
            bucket: { kind: 'missing', value: null, count: 0 }
        });
    });

    it('does not duplicate a selected value already present in buckets', () => {
        const result = buildOptions([value('a', 'foo')], ['foo']);
        expect(result).toHaveLength(1);
        expect(result[0].retained).toBe(false);
    });

    it('places returned buckets before retained ones', () => {
        const result = buildOptions([value('a', 'foo')], ['stale']);
        expect(result[0].retained).toBe(false);
        expect(result[1].retained).toBe(true);
    });

    it('deduplicates absent selected values so each yields exactly one retained option', () => {
        const result = buildOptions([], ['stale', 'stale', null, null]);
        expect(result).toHaveLength(2);
        expect(result[0]).toMatchObject({
            retained: true,
            bucket: { kind: 'value', value: 'stale' }
        });
        expect(result[1]).toMatchObject({
            retained: true,
            bucket: { kind: 'missing', value: null }
        });
    });
});
