import { describe, expect, it } from 'vitest';
import { groupPairRows } from './groupPairRows';
import { buildPairRows, formatCount, summarizeRows } from './pairRows';

const SOURCES = [
    { id: 's1', name: 'ground_truth' },
    { id: 's2', name: 'model' }
];

const count = (collection: string, label: string, name: string, current = 2, total = 4) => ({
    annotation_collection_id: collection,
    annotation_label_id: label,
    label_name: name,
    current_count: current,
    total_count: total
});

describe('buildPairRows', () => {
    it('orders sources as given and classes by name', () => {
        const rows = buildPairRows(
            SOURCES,
            [count('s2', 'l1', 'car'), count('s1', 'l2', 'zebra'), count('s1', 'l1', 'car')],
            [],
            []
        );

        expect(rows.map((row) => [row.sourceName, row.className])).toEqual([
            ['ground_truth', 'car'],
            ['ground_truth', 'zebra'],
            ['model', 'car']
        ]);
    });

    it('marks unticked and hidden pairs', () => {
        const rows = buildPairRows(
            SOURCES,
            [count('s1', 'l1', 'car'), count('s1', 'l2', 'zebra')],
            [{ collection_id: 's1', annotation_label_id: 'l1' }],
            [{ collection_id: 's1', annotation_label_id: 'l2' }]
        );

        expect(rows.map((row) => [row.ticked, row.visible])).toEqual([
            [false, true],
            [true, false]
        ]);
    });
});

describe('summarizeRows', () => {
    const rows = buildPairRows(
        SOURCES,
        [count('s1', 'l1', 'car'), count('s1', 'l2', 'zebra')],
        [{ collection_id: 's1', annotation_label_id: 'l2' }],
        []
    );

    it('is partial when one of two rows is ticked', () => {
        expect(summarizeRows(rows)).toMatchObject({
            tick: 'partial',
            eye: 'on',
            ticked: 1,
            current: 4,
            total: 8
        });
    });

    it('has eye off when every row is hidden', () => {
        const hidden = rows.map((row) => ({ ...row, visible: false }));

        expect(summarizeRows(hidden).eye).toBe('off');
    });
});

describe('formatCount', () => {
    it('shows one number when nothing is filtered out', () => {
        expect(formatCount(5, 5)).toBe('5');
    });

    it('shows current and total otherwise', () => {
        expect(formatCount(3, 5)).toBe('3 / 5');
    });
});

describe('shared class name across sources', () => {
    const sources = [
        { id: 'labels', name: 'labels' },
        { id: 'model_v1', name: 'model_v1' }
    ];
    const rows = buildPairRows(
        sources,
        [count('labels', 'shared', 'car'), count('model_v1', 'shared', 'car')],
        [{ collection_id: 'labels', annotation_label_id: 'shared' }],
        [{ collection_id: 'labels', annotation_label_id: 'shared' }]
    );

    it('stays two pairs with their own tick and visibility', () => {
        expect(rows.map((row) => [row.sourceId, row.ticked, row.visible])).toEqual([
            ['labels', false, false],
            ['model_v1', true, true]
        ]);
    });

    it('keeps their own state in one class group', () => {
        const groups = groupPairRows(rows, 'class', sources);

        expect(groups).toHaveLength(1);
        expect(groups[0].name).toBe('car');
        expect(groups[0].rows.map((row) => [row.sourceId, row.ticked])).toEqual([
            ['labels', false],
            ['model_v1', true]
        ]);
    });
});

describe('summarizeRows without rows', () => {
    it('reads as on with zero counts', () => {
        expect(summarizeRows([])).toEqual({
            tick: 'on',
            eye: 'on',
            ticked: 0,
            current: 0,
            total: 0
        });
    });
});
