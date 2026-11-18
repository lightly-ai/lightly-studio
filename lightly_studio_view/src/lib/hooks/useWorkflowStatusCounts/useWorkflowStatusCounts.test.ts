import * as tanstackQuery from '@tanstack/svelte-query';
import type { CreateQueryOptions, CreateQueryResult, QueryClient } from '@tanstack/svelte-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getWorkflowStatusCountsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useWorkflowStatusCounts } from './useWorkflowStatusCounts.svelte';

const COUNTS = {
    not_in_workflow: 4,
    not_started: 1,
    in_progress: 2,
    in_review: 0,
    rework: 0,
    accepted: 3
};

describe('useWorkflowStatusCounts', () => {
    const queryResult = { data: undefined, dataUpdatedAt: 0 } as {
        data: { counts: typeof COUNTS | null } | undefined;
        dataUpdatedAt: number;
    };
    const invalidateQueries = vi.fn();

    beforeEach(() => {
        vi.restoreAllMocks();
        invalidateQueries.mockReset();
        queryResult.data = undefined;
        queryResult.dataUpdatedAt = 0;
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(
            queryResult as unknown as CreateQueryResult
        );
        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue({
            invalidateQueries
        } as unknown as QueryClient);
    });

    const options = () =>
        vi.mocked(tanstackQuery.createQuery).mock.calls[0][0]() as CreateQueryOptions;

    it('requests the counts of the collection when the dataset has a project', () => {
        useWorkflowStatusCounts(() => ({ collectionId: 'collection-1', projectId: 'project-1' }));

        expect(options().queryKey).toEqual(
            getWorkflowStatusCountsOptions({ path: { collection_id: 'collection-1' } }).queryKey
        );
        expect(options().enabled).toBe(true);
    });

    it('makes no request when the dataset has no project', () => {
        useWorkflowStatusCounts(() => ({ collectionId: 'collection-1', projectId: null }));

        expect(options().enabled).toBe(false);
    });

    it('exposes the counts, and null while loading', () => {
        const status = useWorkflowStatusCounts(() => ({
            collectionId: 'collection-1',
            projectId: 'project-1'
        }));
        expect(status.counts).toBeNull();

        queryResult.data = { counts: COUNTS };

        expect(status.counts).toEqual(COUNTS);
    });

    it('refreshes counts older than a grid reload, joining a fetch in flight', () => {
        const status = useWorkflowStatusCounts(() => ({
            collectionId: 'collection-1',
            projectId: 'project-1'
        }));
        queryResult.dataUpdatedAt = 100;

        status.refreshIfOlderThan(200);

        expect(invalidateQueries).toHaveBeenCalledWith(
            {
                queryKey: getWorkflowStatusCountsOptions({
                    path: { collection_id: 'collection-1' }
                }).queryKey
            },
            { cancelRefetch: false }
        );
    });

    it('keeps counts fetched after the grid reload started', () => {
        const status = useWorkflowStatusCounts(() => ({
            collectionId: 'collection-1',
            projectId: 'project-1'
        }));
        queryResult.dataUpdatedAt = 300;

        status.refreshIfOlderThan(200);

        expect(invalidateQueries).not.toHaveBeenCalled();
    });

    it('never refreshes without a project', () => {
        const status = useWorkflowStatusCounts(() => ({
            collectionId: 'collection-1',
            projectId: null
        }));

        status.refreshIfOlderThan(200);

        expect(invalidateQueries).not.toHaveBeenCalled();
    });
});
