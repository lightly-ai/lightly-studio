import { describe, expect, it } from 'vitest';
import { createAccumulatedFrameSelector } from './createAccumulatedFrameSelector';

const frame = (channelId: number) => ({
    batch: {
        positions: new Float32Array([channelId, 0, 0]),
        intensities: new Float32Array([1]),
        count: 1
    },
    channelId,
    timestampNs: '100',
    frameId: 'map',
    sourcePointCount: 1,
    bounds: null,
    channels: [{ channelId, timestampNs: '100', frameId: 'map' }]
});

describe('accumulation selection', () => {
    it('keeps the previous batch for repeated placeholder data, then updates for new ticks or channels', () => {
        const select = createAccumulatedFrameSelector();
        const tick = { pointClouds: [frame(1), frame(2)], cameraFrames: {} };
        const first = select([tick]);
        expect(select([tick])).toBe(first);
        const selected = select([tick], [2]);
        expect(selected.batch.count).toBe(1);
        expect(selected.channels[0].channelId).toBe(2);
        expect(select([tick], [2])).toBe(selected);
        const next = { pointClouds: [{ ...frame(2), timestampNs: '200' }], cameraFrames: {} };
        expect(select([tick, next], [2]).batch.count).toBe(2);
    });
});
