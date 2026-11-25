import type { TickData } from '$lib/hooks/useTickData/fetchTickData';
import { mergeCloudPointFrames } from './mergeCloudPointFrames';
import type { CloudPointFrame } from './types';

/** Merges each selected sensor capture once, even when neighboring ticks share it. */
export function mergeAccumulatedFrames(
    ticks: TickData[],
    selectedChannelIds?: number[]
): CloudPointFrame {
    const seen = new Set<string>();
    const [first, ...rest] = ticks
        .flatMap((tick) => tick.pointClouds)
        .filter((frame) => {
            if (selectedChannelIds && !selectedChannelIds.includes(frame.channelId)) return false;
            const key = JSON.stringify([frame.channelId, frame.timestampNs, frame.frameId]);
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    if (!first) throw new Error('No point cloud channels to load.');
    return rest.length ? mergeCloudPointFrames([first, ...rest], { segmented: true }) : first;
}
