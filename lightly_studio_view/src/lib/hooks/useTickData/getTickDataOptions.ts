import { fetchTickData, type TickDataParams } from './fetchTickData';

/** Builds the cached query for one tick's sensor data, shared by every view and the prefetch. */
export const getTickDataOptions = (params: TickDataParams) => ({
    queryKey: [
        'tick-data',
        params.datasetId,
        params.sequenceId,
        params.seqNumber,
        params.displayFrameId ?? ''
    ],
    queryFn: ({ signal }: { signal?: AbortSignal }) => fetchTickData(params, signal)
});
