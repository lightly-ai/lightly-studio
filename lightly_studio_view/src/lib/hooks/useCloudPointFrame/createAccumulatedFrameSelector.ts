import type { TickData } from '$lib/hooks/useTickData/fetchTickData';
import { mergeAccumulatedFrames } from './mergeAccumulatedFrames';
import type { CloudPointFrame } from './types';

/** Keeps the displayed batch stable when a query reselects the same sensor snapshots. */
export function createAccumulatedFrameSelector() {
    let previousTicks: TickData[] = [];
    let previousChannels: string | undefined;
    let previousFrame: CloudPointFrame | undefined;
    return (ticks: TickData[], selectedChannelIds?: number[]): CloudPointFrame => {
        const channels = JSON.stringify(selectedChannelIds);
        if (
            previousFrame &&
            channels === previousChannels &&
            ticks.length === previousTicks.length &&
            ticks.every((tick, index) => tick === previousTicks[index])
        )
            return previousFrame;
        const frame = mergeAccumulatedFrames(ticks, selectedChannelIds);
        previousTicks = ticks;
        previousChannels = channels;
        previousFrame = frame;
        return frame;
    };
}
