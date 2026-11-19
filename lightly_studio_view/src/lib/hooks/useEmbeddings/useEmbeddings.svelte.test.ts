import { QueryClient } from '@tanstack/svelte-query';
import { render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get2dEmbeddings } from '$lib/api/lightly_studio_local/sdk.gen';
import type { useEmbeddings } from './useEmbeddings';
import UseEmbeddingsTest from './UseEmbeddings.test.svelte';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    get2dEmbeddings: vi.fn()
}));
vi.mock('apache-arrow', () => ({
    tableFromIPC: vi.fn(() => ({
        schema: { metadata: new Map([['color_legend', '{"3":"car"}']]) },
        getChild: () => ({ length: 0, toArray: () => [] })
    }))
}));

type Params = ReturnType<Parameters<typeof useEmbeddings>[0]>;

const FIRST_LEGEND = new Map([[3, 'car']]);
const LAYOUT_CHANGES: [string, Partial<Params>][] = [
    ['color-by', { colorBy: { type: 'tag', tag_ids: ['tag-a'] } }],
    ['axes', { axes: { x: [1, 0], y: [0, 1] } }],
    ['collection', { collectionId: 'collection-2' }]
];

const renderEmbeddings = (enabled: boolean) => {
    const params: Params = $state({
        collectionId: 'c',
        filters: null,
        colorBy: null,
        axes: null,
        enabled
    });
    let query!: ReturnType<typeof useEmbeddings>;
    const onQuery = (created: typeof query) => (query = created);
    render(UseEmbeddingsTest, {
        queryClient: new QueryClient({ defaultOptions: { queries: { retry: false } } }),
        getParams: () => params,
        onQuery
    });
    return { params, query };
};

const renderLoaded = async () => {
    const rendered = renderEmbeddings(true);
    await waitFor(() => expect(rendered.query.data?.legend).toEqual(FIRST_LEGEND));
    return rendered;
};

describe('useEmbeddings', () => {
    beforeEach(() => {
        vi.mocked(get2dEmbeddings)
            .mockReset()
            .mockResolvedValueOnce({ data: new ArrayBuffer(8) } as never)
            .mockReturnValue(new Promise(() => {}) as never);
    });

    it('keeps the previous points and legend while a filter change loads', async () => {
        const { params, query } = await renderLoaded();
        const firstLegend = query.data?.legend;
        params.filters = { filter_type: 'image', sample_filter: { tag_ids: ['tag-a'] } };

        await waitFor(() => expect(get2dEmbeddings).toHaveBeenCalledTimes(2));
        expect(query.isPlaceholderData).toBe(true);
        expect(query.data?.legend).toBe(firstLegend);
    });

    it.each(LAYOUT_CHANGES)('drops the previous points when the %s changes', async (_, change) => {
        const { params, query } = await renderLoaded();
        Object.assign(params, change);

        await waitFor(() => expect(get2dEmbeddings).toHaveBeenCalledTimes(2));
        expect(query.isPlaceholderData).toBe(false);
        expect(query.data).toBeUndefined();
    });

    it('drops the previous points when a filter change fails', async () => {
        const { params, query } = await renderLoaded();
        vi.mocked(get2dEmbeddings).mockRejectedValueOnce(new Error('failed'));
        params.filters = { filter_type: 'image', sample_filter: { tag_ids: ['tag-a'] } };

        await waitFor(() => expect(query.isError).toBe(true));
        expect(query.data).toBeUndefined();
    });

    it('sends no request while disabled', async () => {
        const { query } = renderEmbeddings(false);

        await Promise.resolve();
        expect(get2dEmbeddings).not.toHaveBeenCalled();
        expect(query.isPending).toBe(true);
    });
});
