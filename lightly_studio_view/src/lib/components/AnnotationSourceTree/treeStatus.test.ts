import { describe, expect, it } from 'vitest';
import { applyStatusAction, getTreeStatus } from './treeStatus';
import { createMatcher, matchRows } from './treeSearch';
import { toNamedPair } from './pairRows';
import { testRows } from './testRows';

const ticked = (unticked: ReturnType<typeof applyStatusAction>['unticked']) =>
    testRows(unticked)
        .filter((row) => row.ticked)
        .map((row) => `${row.sourceId}/${row.className}`);

describe('getTreeStatus', () => {
    it('shows everything with no actions while all is ticked', () => {
        const rows = testRows();
        expect(
            getTreeStatus({ rows, matches: rows, searching: false, unannotatedTicked: true })
        ).toEqual({ text: 'Showing everything', actions: [] });
    });

    it('counts "No annotations" and offers show all and hide all', () => {
        const rows = testRows([toNamedPair(testRows()[0])]);
        expect(
            getTreeStatus({ rows, matches: rows, searching: false, unannotatedTicked: true })
        ).toEqual({ text: '1 hidden', actions: ['showAll', 'hideAll'] });
    });

    it('offers only the search actions that change something', () => {
        const rows = testRows();
        const matches = matchRows(rows, createMatcher('deer', false));

        expect(getTreeStatus({ rows, matches, searching: true })).toEqual({
            text: '2 matches',
            actions: ['showOnly', 'hide']
        });

        const deerUnticked = testRows(matches.map(toNamedPair));
        const deerMatches = matchRows(deerUnticked, createMatcher('deer', false));
        expect(
            getTreeStatus({ rows: deerUnticked, matches: deerMatches, searching: true })
        ).toEqual({ text: '2 matches', actions: ['showOnly', 'add'] });
        expect(getTreeStatus({ rows, matches: [], searching: true }).text).toBe('No matches');
    });
});

it('says everything is hidden when nothing is ticked', () => {
    const rows = testRows(testRows().map(toNamedPair));
    expect(
        getTreeStatus({ rows, matches: rows, searching: false, unannotatedTicked: false })
    ).toEqual({ text: 'Everything hidden', actions: ['showAll'] });
});

describe('applyStatusAction', () => {
    const rows = testRows();
    const matches = matchRows(rows, createMatcher('deer', false));
    const raccoon = toNamedPair(rows[3]);

    it('shows only, adds and hides the matches', () => {
        const showOnly = applyStatusAction('showOnly', { rows, matches, unticked: [] });
        expect(ticked(showOnly.unticked)).toEqual(['gt/Deer', 'model/Deer']);
        expect(showOnly.unannotatedTicked).toBe(false);

        const allUnticked = rows.map(toNamedPair);
        expect(
            ticked(applyStatusAction('add', { rows, matches, unticked: allUnticked }).unticked)
        ).toEqual(['gt/Deer', 'model/Deer']);
        expect(
            ticked(applyStatusAction('hide', { rows, matches, unticked: [raccoon] }).unticked)
        ).toEqual(['gt/car']);
    });

    it('shows all and hides all', () => {
        expect(applyStatusAction('showAll', { rows, matches, unticked: [raccoon] })).toEqual({
            unticked: [],
            unannotatedTicked: true
        });
        const hideAll = applyStatusAction('hideAll', { rows, matches, unticked: [] });
        expect(ticked(hideAll.unticked)).toEqual([]);
        expect(hideAll.unannotatedTicked).toBe(false);
    });
});
