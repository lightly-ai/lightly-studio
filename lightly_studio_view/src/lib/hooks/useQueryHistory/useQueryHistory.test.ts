import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

let useQueryHistory: typeof import('./useQueryHistory').useQueryHistory;

describe('useQueryHistory', () => {
    // The history lives in module state backed by localStorage. Start each test fresh.
    beforeEach(async () => {
        localStorage.clear();
        vi.resetModules();
        ({ useQueryHistory } = await import('./useQueryHistory'));
    });

    it('puts the newest query first and keeps one entry per query', () => {
        const { queryHistory, addQuery } = useQueryHistory();

        addQuery('col-1', 'width > 100');
        addQuery('col-1', 'height > 100');
        addQuery('col-1', 'width > 100');

        expect(get(queryHistory)['col-1']).toEqual(['width > 100', 'height > 100']);
    });

    it('keeps at most 10 queries', () => {
        const { queryHistory, addQuery } = useQueryHistory();

        for (let width = 0; width < 12; width++) {
            addQuery('col-1', `width > ${width}`);
        }

        const queries = get(queryHistory)['col-1'];
        expect(queries).toHaveLength(10);
        expect(queries[0]).toBe('width > 11');
        expect(queries[9]).toBe('width > 2');
    });

    it('keeps a separate history for each collection', () => {
        const { queryHistory, addQuery } = useQueryHistory();

        addQuery('col-1', 'width > 100');
        addQuery('col-2', 'height > 100');

        expect(get(queryHistory)).toEqual({
            'col-1': ['width > 100'],
            'col-2': ['height > 100']
        });
    });

    it('persists the history in localStorage', async () => {
        useQueryHistory().addQuery('col-1', 'width > 100');

        vi.resetModules();
        ({ useQueryHistory } = await import('./useQueryHistory'));

        expect(get(useQueryHistory().queryHistory)['col-1']).toEqual(['width > 100']);
    });
});
