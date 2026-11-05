import { describe, expect, it } from 'vitest';
import { matchClasses, matchSources, recentChips } from './searchRanking';

describe('matchClasses', () => {
    const names = ['bobcat', 'coyote', 'deer', 'raccoon'];

    it('lists recent classes first for an empty query', () => {
        expect(matchClasses({ names, recent: ['deer', 'coyote'], query: '' })).toEqual({
            matches: ['deer', 'coyote', 'bobcat', 'raccoon'],
            createName: null
        });
    });

    it('lists the current class first, before the recent classes', () => {
        expect(
            matchClasses({ names, recent: ['deer', 'coyote'], current: 'raccoon', query: '' })
        ).toEqual({ matches: ['raccoon', 'deer', 'coyote', 'bobcat'], createName: null });
    });

    it('keeps the current class inside its match tier', () => {
        expect(
            matchClasses({ names, recent: [], current: 'raccoon', query: 'co' }).matches
        ).toEqual(['coyote', 'raccoon']);
    });

    it('matches by substring and offers to create', () => {
        expect(matchClasses({ names, recent: [], query: 'co' })).toEqual({
            matches: ['coyote', 'raccoon'],
            createName: 'co'
        });
    });

    it('orders exact, prefix, then substring', () => {
        expect(
            matchClasses({ names: ['bobcat', 'category', 'cat'], recent: [], query: 'cat' })
        ).toEqual({ matches: ['cat', 'category', 'bobcat'], createName: null });
    });

    it('puts recent classes first within a tier', () => {
        expect(
            matchClasses({ names: ['cat', 'car', 'cab'], recent: ['cab'], query: 'ca' })
        ).toEqual({ matches: ['cab', 'car', 'cat'], createName: 'ca' });
    });

    it('ignores case', () => {
        expect(matchClasses({ names, recent: [], query: 'DEER' })).toEqual({
            matches: ['deer'],
            createName: null
        });
    });

    it('trims the query', () => {
        expect(matchClasses({ names, recent: [], query: '  fox ' })).toEqual({
            matches: [],
            createName: 'fox'
        });
    });
});

describe('matchSources', () => {
    const sources = [{ name: 'predictions' }, { name: 'labels' }, { name: 'model-preds' }];

    it('sorts alphabetically for an empty query', () => {
        expect(matchSources({ sources, query: '' }).map((s) => s.name)).toEqual([
            'labels',
            'model-preds',
            'predictions'
        ]);
    });

    it('puts prefix matches before substring matches', () => {
        expect(matchSources({ sources, query: 'PRE' }).map((s) => s.name)).toEqual([
            'predictions',
            'model-preds'
        ]);
    });
});

describe('recentChips', () => {
    const list = ['deer', 'bobcat', 'coyote', 'fox'];

    it('skips the current class', () => {
        expect(recentChips(list, 'deer')).toEqual(['bobcat', 'coyote', 'fox']);
    });

    it('keeps the first three without a current class', () => {
        expect(recentChips(list, null)).toEqual(['deer', 'bobcat', 'coyote']);
    });
});
