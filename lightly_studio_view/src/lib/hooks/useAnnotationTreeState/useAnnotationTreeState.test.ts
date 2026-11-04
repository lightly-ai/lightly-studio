import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { PairKey } from '$lib/components/AnnotationTree/pairRows';
import { useAnnotationTreeState } from './useAnnotationTreeState';

const pair = (collection_id: string, annotation_label_id: string): PairKey => ({
    collection_id,
    annotation_label_id
});

describe('useAnnotationTreeState', () => {
    let id = 0;
    let collectionId: string;

    beforeEach(() => {
        collectionId = `collection-${id++}`;
    });

    it('keeps separate state per collection', () => {
        const first = useAnnotationTreeState(collectionId);
        const second = useAnnotationTreeState(`${collectionId}-other`);

        first.setTicked([pair('s1', 'a')], false);
        first.setGroupBy('class');

        expect(get(first.untickedPairs)).toEqual([pair('s1', 'a')]);
        expect(get(first.groupBy)).toBe('class');
        expect(get(second.untickedPairs)).toEqual([]);
        expect(get(second.groupBy)).toBe('source');
    });

    it('persists the state in session storage', () => {
        useAnnotationTreeState(collectionId).setVisible([pair('s1', 'a')], false);

        const stored = JSON.parse(sessionStorage.getItem('lightlyStudio_annotation_tree') ?? '{}');
        expect(stored[collectionId].hiddenPairs).toEqual([pair('s1', 'a')]);
    });

    it('does not duplicate entries', () => {
        const state = useAnnotationTreeState(collectionId);

        state.setTicked([pair('s1', 'a'), pair('s1', 'a')], false);
        state.setTicked([pair('s1', 'a')], false);
        state.setVisible([pair('s1', 'a')], false);
        state.setVisible([pair('s1', 'a')], false);
        state.setUnannotatedTicked(['s1', 's1'], false);
        state.setUnannotatedTicked(['s1'], false);

        expect(get(state.untickedPairs)).toEqual([pair('s1', 'a')]);
        expect(get(state.hiddenPairs)).toEqual([pair('s1', 'a')]);
        expect(get(state.untickedUnannotated)).toEqual(['s1']);
    });

    it('ticks and shows pairs again', () => {
        const state = useAnnotationTreeState(collectionId);
        state.setTicked([pair('s1', 'a'), pair('s1', 'b')], false);
        state.setVisible([pair('s1', 'a')], false);
        state.setUnannotatedTicked(['s1'], false);

        state.setTicked([pair('s1', 'a')], true);
        state.setVisible([pair('s1', 'a')], true);
        state.setUnannotatedTicked(['s1'], true);

        expect(get(state.untickedPairs)).toEqual([pair('s1', 'b')]);
        expect(get(state.hiddenPairs)).toEqual([]);
        expect(get(state.untickedUnannotated)).toEqual([]);
    });

    it('resetTicks leaves hiddenPairs unchanged', () => {
        const state = useAnnotationTreeState(collectionId);
        state.setTicked([pair('s1', 'a')], false);
        state.setUnannotatedTicked(['s1'], false);
        state.setVisible([pair('s1', 'b')], false);

        state.resetTicks();

        expect(get(state.untickedPairs)).toEqual([]);
        expect(get(state.untickedUnannotated)).toEqual([]);
        expect(get(state.hiddenPairs)).toEqual([pair('s1', 'b')]);
    });

    it('only unticks every other pair and ticks the given ones', () => {
        const state = useAnnotationTreeState(collectionId);
        const all = [pair('s1', 'a'), pair('s1', 'b'), pair('s2', 'a')];
        state.setTicked([pair('s1', 'a')], false);
        state.setUnannotatedTicked(['s1'], false);

        state.only([pair('s1', 'a')], all);

        expect(get(state.untickedPairs)).toEqual([pair('s1', 'b'), pair('s2', 'a')]);
        expect(get(state.untickedUnannotated)).toEqual(['s1']);
    });

    it('toggleOpen flips the group and honours the current state of a default group', () => {
        const state = useAnnotationTreeState(collectionId);

        state.toggleOpen('g1');
        state.toggleOpen('g2', false);
        state.toggleOpen('g3', false);
        state.toggleOpen('g3', false);

        expect(get(state.openGroups)).toEqual({ g1: false, g2: true, g3: false });
    });

    it('dropSource removes that source entries only', () => {
        const state = useAnnotationTreeState(collectionId);
        state.setTicked([pair('s1', 'a'), pair('s2', 'a')], false);
        state.setVisible([pair('s1', 'b'), pair('s2', 'b')], false);
        state.setUnannotatedTicked(['s1', 's2'], false);
        state.toggleOpen('s1');
        state.toggleOpen('s2');

        state.dropSource('s1');

        expect(get(state.untickedPairs)).toEqual([pair('s2', 'a')]);
        expect(get(state.hiddenPairs)).toEqual([pair('s2', 'b')]);
        expect(get(state.untickedUnannotated)).toEqual(['s2']);
        expect(get(state.openGroups)).toEqual({ s2: false });
    });

    describe('hydration from session storage', () => {
        const KEY = 'lightlyStudio_annotation_tree';

        const load = async (stored: unknown) => {
            sessionStorage.setItem(KEY, JSON.stringify(stored));
            vi.resetModules();
            const module = await import('./useAnnotationTreeState');
            return module.useAnnotationTreeState('c1');
        };

        it('reads a valid stored entry back', async () => {
            const state = await load({
                c1: {
                    untickedPairs: [pair('s1', 'a')],
                    untickedUnannotated: ['s1'],
                    hiddenPairs: [pair('s1', 'b')],
                    groupBy: 'class',
                    openGroups: { g: true }
                }
            });

            expect(get(state.untickedPairs)).toEqual([pair('s1', 'a')]);
            expect(get(state.untickedUnannotated)).toEqual(['s1']);
            expect(get(state.hiddenPairs)).toEqual([pair('s1', 'b')]);
            expect(get(state.groupBy)).toBe('class');
            expect(get(state.openGroups)).toEqual({ g: true });
        });

        it('treats a stored null as the empty state', async () => {
            const state = await load(null);

            expect(get(state.untickedPairs)).toEqual([]);
            expect(get(state.groupBy)).toBe('source');
            state.setTicked([pair('s1', 'a')], false);
            expect(get(state.untickedPairs)).toEqual([pair('s1', 'a')]);
        });

        it('fills missing fields of an entry with defaults', async () => {
            const state = await load({ c1: { groupBy: 'class' } });

            expect(get(state.groupBy)).toBe('class');
            expect(get(state.untickedPairs)).toEqual([]);
            expect(get(state.openGroups)).toEqual({});
            state.setVisible([pair('s1', 'a')], false);
            expect(get(state.hiddenPairs)).toEqual([pair('s1', 'a')]);
        });
    });
});
