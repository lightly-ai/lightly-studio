import { get, writable } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useSplitForm } from './useSplitForm';

function setup(sampleCount = 100, existingNames: string[] = []) {
    const filteredSampleCount = writable(sampleCount);
    const existingTagNames = writable(existingNames);
    const form = useSplitForm({ filteredSampleCount, existingTagNames });
    return { form, filteredSampleCount, existingTagNames };
}

describe('useSplitForm', () => {
    it('starts valid with the default train/val/test rows', () => {
        const { form } = setup();
        expect(get(form.percentageSum)).toBe(100);
        expect(get(form.isValid)).toBe(true);
        expect(get(form.errorMessage)).toBeNull();
    });

    it('flags an error when percentages do not sum to 100', () => {
        const { form } = setup();
        const rows = get(form.rows);
        form.updatePercentage(rows[0].id, 50);
        expect(get(form.isValid)).toBe(false);
        expect(get(form.errorMessage)).toContain('sum to 100');
    });

    it('flags duplicate split names', () => {
        const { form } = setup();
        const rows = get(form.rows);
        form.updateName(rows[1].id, 'train');
        expect(get(form.errorMessage)).toContain('unique');
    });

    it('adds and removes rows', () => {
        const { form } = setup();
        form.addRow();
        expect(get(form.rows)).toHaveLength(4);
        const rows = get(form.rows);
        form.removeRow(rows[3].id);
        expect(get(form.rows)).toHaveLength(3);
    });

    it('previews per-split counts against the filtered set', () => {
        const { form } = setup(1000);
        expect(get(form.previewCounts)).toEqual({ train: 800, val: 100, test: 100 });
    });

    it('reports which target splits already exist as tags', () => {
        const { form } = setup(100, ['train', 'other']);
        expect(get(form.overwrittenTagNames)).toEqual(['train']);
    });

    it('exposes trimmed sizes for submission', () => {
        const { form } = setup();
        expect(form.getSizes()).toEqual({ train: 80, val: 10, test: 10 });
    });
});
