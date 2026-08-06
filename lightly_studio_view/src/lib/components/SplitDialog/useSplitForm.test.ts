import { get, writable } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useSplitForm } from './useSplitForm';

function setup(sampleCount = 100) {
    const filteredSampleCount = writable(sampleCount);
    const form = useSplitForm({ filteredSampleCount });
    return { form, filteredSampleCount };
}

describe('useSplitForm', () => {
    it('starts valid with the default train/val/test rows in 80:10:10 parts', () => {
        const { form } = setup();
        expect(get(form.rows).map((row) => row.parts)).toEqual([80, 10, 10]);
        expect(get(form.isValid)).toBe(true);
        expect(get(form.errorMessage)).toBeNull();
    });

    it('edits a row without touching the others', () => {
        const { form } = setup();
        const [train] = get(form.rows);
        form.updateParts(train.id, 3);
        expect(get(form.rows).map((row) => row.parts)).toEqual([3, 10, 10]);
        expect(get(form.isValid)).toBe(true);
    });

    it('derives percentage and sample count from the relative parts', () => {
        const { form } = setup(1000);
        const preview = get(form.preview);
        const rows = get(form.rows);
        expect(preview[rows[0].id]).toEqual({ percentage: 80, count: 800 });
        expect(preview[rows[1].id]).toEqual({ percentage: 10, count: 100 });
        expect(preview[rows[2].id]).toEqual({ percentage: 10, count: 100 });
    });

    it('recomputes the preview when parts change', () => {
        const { form } = setup(100);
        const rows = get(form.rows);
        // 1:1:1 -> even thirds; largest-remainder hands the leftover to the first.
        rows.forEach((row) => form.updateParts(row.id, 1));
        const preview = get(form.preview);
        expect(preview[rows[0].id]).toEqual({ percentage: 33, count: 34 });
        expect(preview[rows[1].id]).toEqual({ percentage: 33, count: 33 });
        expect(preview[rows[2].id]).toEqual({ percentage: 33, count: 33 });
    });

    it('flags duplicate split names', () => {
        const { form } = setup();
        const rows = get(form.rows);
        form.updateName(rows[1].id, 'train');
        expect(get(form.errorMessage)).toContain('unique');
    });

    it('flags a split with non-positive parts', () => {
        const { form } = setup();
        const [train] = get(form.rows);
        form.updateParts(train.id, 0);
        expect(get(form.errorMessage)).toContain('at least 1 part');
    });

    it('adds a row with a default of one part', () => {
        const { form } = setup();
        form.addRow();
        const rows = get(form.rows);
        expect(rows).toHaveLength(4);
        expect(rows[3].parts).toBe(1);
    });

    it('removes a row without redistributing parts', () => {
        const { form } = setup();
        const val = get(form.rows)[1];
        form.removeRow(val.id);
        const rows = get(form.rows);
        expect(rows.map((row) => row.name)).toEqual(['train', 'test']);
        expect(rows.map((row) => row.parts)).toEqual([80, 10]);
    });

    it('exposes trimmed sizes for submission', () => {
        const { form } = setup();
        expect(form.getSizes()).toEqual({ train: 80, val: 10, test: 10 });
    });
});
