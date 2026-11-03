import { QueryClient } from '@tanstack/svelte-query';
import { render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { countTagsForSelection } from '$lib/api/lightly_studio_local/sdk.gen';
import UseSelectionTagCountsHarness from './UseSelectionTagCountsHarness.svelte';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async () => ({
    ...(await vi.importActual('$lib/api/lightly_studio_local/sdk.gen')),
    countTagsForSelection: vi.fn()
}));

beforeEach(() => {
    vi.mocked(countTagsForSelection).mockReset();
    vi.mocked(countTagsForSelection).mockResolvedValue({
        data: [{ tag_id: 'a', count: 2 }]
    } as never);
});

describe('useSelectionTagCounts', () => {
    it('maps tag IDs to counts and refetches when the target changes', async () => {
        const { getByTestId, rerender } = render(UseSelectionTagCountsHarness, {
            props: { client: new QueryClient(), target: { kind: 'ids', ids: ['s1'] } }
        });
        await waitFor(() => expect(getByTestId('counts')).toHaveTextContent('a=2'));
        expect(countTagsForSelection).toHaveBeenLastCalledWith(
            expect.objectContaining({ body: { sample_ids: ['s1'] } })
        );

        await rerender({ target: { kind: 'filter', filter: { filter_type: 'image' }, size: 5 } });
        await waitFor(() =>
            expect(countTagsForSelection).toHaveBeenLastCalledWith(
                expect.objectContaining({ body: { filter: { filter_type: 'image' } } })
            )
        );
        expect(countTagsForSelection).toHaveBeenCalledTimes(2);
    });
});
