import { get, writable } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useSplitForm } from './useSplitForm';

function setup(sampleCount = 100) {
    const filteredSampleCount = writable(sampleCount);
    const form = useSplitForm({ filteredSampleCount });
    return { form, filteredSampleCount };
}

function sumOf(rows: { percentage: number }[]): number {
    return rows.reduce((sum, row) => sum + row.percentage, 0);
}

describe('useSplitForm', () => {
    it('starts valid with the default train/val/test rows summing to 100', () => {
        const { form } = setup();
        expect(sumOf(get(form.rows))).toBe(100);
        expect(get(form.isValid)).toBe(true);
        expect(get(form.errorMessage)).toBeNull();
    });

    it('absorbs an edit into the next row so the total stays 100', () => {
        const { form } = setup();
        const [train, val, test] = get(form.rows);
        // train 80 -> 70 pushes +10 into val (10 -> 20); test untouched.
        form.updatePercentage(train.id, 70);
        const rows = get(form.rows);
        expect(rows.map((row) => row.percentage)).toEqual([70, 20, 10]);
        expect(sumOf(rows)).toBe(100);
        expect(val.id).toBe(rows[1].id);
        expect(test.id).toBe(rows[2].id);
    });

    it('clamps an edit so the next row never goes below 0', () => {
        const { form } = setup();
        const [train] = get(form.rows);
        // val only has 10 to give, so train tops out at 90.
        form.updatePercentage(train.id, 95);
        const rows = get(form.rows);
        expect(rows.map((row) => row.percentage)).toEqual([90, 0, 10]);
        expect(sumOf(rows)).toBe(100);
    });

    it('wraps the absorbed delta from the last row into the first', () => {
        const { form } = setup();
        const rows = get(form.rows);
        const test = rows[2];
        // Editing the last row pushes the delta into the first (train).
        form.updatePercentage(test.id, 30);
        const updated = get(form.rows);
        expect(updated.map((row) => row.percentage)).toEqual([60, 10, 30]);
        expect(sumOf(updated)).toBe(100);
    });

    it('flags duplicate split names', () => {
        const { form } = setup();
        const rows = get(form.rows);
        form.updateName(rows[1].id, 'train');
        expect(get(form.errorMessage)).toContain('unique');
    });

    it('flags a split with a non-positive percentage', () => {
        const { form } = setup();
        const [train] = get(form.rows);
        form.updatePercentage(train.id, 90); // drives val to 0
        expect(get(form.errorMessage)).toContain('greater than 0');
    });

    it('adds a row by carving its share out of the last row, keeping the total 100', () => {
        const { form } = setup();
        form.addRow();
        const rows = get(form.rows);
        expect(rows).toHaveLength(4);
        // test 10 -> 5, new row gets 5.
        expect(rows[2].percentage).toBe(5);
        expect(rows[3].percentage).toBe(5);
        expect(sumOf(rows)).toBe(100);
    });

    it('removes a row by donating its share to the next row, keeping the total 100', () => {
        const { form } = setup();
        const val = get(form.rows)[1];
        form.removeRow(val.id);
        const rows = get(form.rows);
        expect(rows.map((row) => row.name)).toEqual(['train', 'test']);
        // val's 10 goes to the following row (test): 10 -> 20.
        expect(rows.map((row) => row.percentage)).toEqual([80, 20]);
        expect(sumOf(rows)).toBe(100);
    });

    it('wraps a removed last row donation into the first row', () => {
        const { form } = setup();
        const test = get(form.rows)[2];
        form.removeRow(test.id);
        const rows = get(form.rows);
        expect(rows.map((row) => row.name)).toEqual(['train', 'val']);
        expect(rows.map((row) => row.percentage)).toEqual([90, 10]);
        expect(sumOf(rows)).toBe(100);
    });

    it('previews per-split counts against the filtered set', () => {
        const { form } = setup(1000);
        expect(get(form.previewCounts)).toEqual({ train: 800, val: 100, test: 100 });
    });

    it('exposes trimmed sizes for submission', () => {
        const { form } = setup();
        expect(form.getSizes()).toEqual({ train: 80, val: 10, test: 10 });
    });
});
