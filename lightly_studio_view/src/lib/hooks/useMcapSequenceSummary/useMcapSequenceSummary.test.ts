import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useMcapSequenceSummary } from './useMcapSequenceSummary';
import type { QueryClient, CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';

describe('useMcapSequenceSummary', () => {
    const mockInvalidateQueries = vi.fn();
    const mockQueryClient: Pick<QueryClient, 'invalidateQueries'> = {
        invalidateQueries: mockInvalidateQueries
    };

    const mockSummary = {
        recording_id: 'rec-1',
        format: 'mcap',
        start_log_time_ns: 1000000,
        lidar_channels: [
            {
                channel_id: 1,
                group_component_name: 'lidar',
                group_component_index: 0,
                frame_id: 'base_link'
            }
        ],
        camera_channels: [
            {
                channel_id: 2,
                group_component_name: 'front',
                group_component_index: 0,
                frame_id: 'camera_front'
            }
        ]
    };

    const mockQueryResult = {
        data: mockSummary,
        isSuccess: true,
        isLoading: false,
        error: null
    };

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(tanstackQuery, 'useQueryClient').mockReturnValue(mockQueryClient as QueryClient);
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(
            mockQueryResult as unknown as CreateQueryResult<unknown, Error>
        );
    });

    it('should return summary and refetch', () => {
        const result = useMcapSequenceSummary({
            getDatasetId: () => 'dataset-1',
            getSequenceId: () => 'seq-1'
        });

        expect(result.summary).toBeDefined();
        expect(result.refetch).toBeDefined();
        expect(typeof result.refetch).toBe('function');
    });

    it('should call createQuery with correct path options', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        useMcapSequenceSummary({
            getDatasetId: () => 'dataset-1',
            getSequenceId: () => 'seq-1'
        });

        const optionsArg = createQuerySpy.mock.calls[0][0]();
        expect(optionsArg).toEqual(
            expect.objectContaining({
                queryKey: expect.any(Array)
            })
        );
    });

    it('should call invalidateQueries when refetch is called', () => {
        const { refetch } = useMcapSequenceSummary({
            getDatasetId: () => 'dataset-1',
            getSequenceId: () => 'seq-1'
        });

        refetch();

        expect(mockInvalidateQueries).toHaveBeenCalledWith({
            queryKey: expect.any(Array)
        });
    });

    it('should return summary data with lidar and camera channels', () => {
        const { summary } = useMcapSequenceSummary({
            getDatasetId: () => 'dataset-1',
            getSequenceId: () => 'seq-1'
        });

        expect(summary.data?.lidar_channels).toHaveLength(1);
        expect(summary.data?.camera_channels).toHaveLength(1);
        expect(summary.data?.lidar_channels[0].group_component_name).toBe('lidar');
        expect(summary.data?.camera_channels[0].group_component_name).toBe('front');
    });
});
