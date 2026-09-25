import { describe, expect, it, vi } from 'vitest';
import { Table, tableFromIPC } from 'apache-arrow';
import { parseCloudPointFrame } from './useCloudPointFrame.svelte';

vi.mock('apache-arrow', () => ({ tableFromIPC: vi.fn() }));

describe('parseCloudPointFrame', () => {
    it('packs xyz columns and reads frame metadata', async () => {
        const table = {
            schema: {
                metadata: new Map([
                    ['frame_id', 'lidar'],
                    ['log_time_ns', '1788220800123000000'],
                    ['source_point_count', '2'],
                    ['bounds', '{"min":[1,2,3],"max":[4,5,6]}']
                ])
            },
            getChild: (name: string) => {
                const values: Record<string, Float32Array> = {
                    x: new Float32Array([1, 4]),
                    y: new Float32Array([2, 5]),
                    z: new Float32Array([3, 6]),
                    intensity: new Float32Array([0.25, 0.75]),
                    r: new Float32Array([0.1, 0.4]),
                    g: new Float32Array([0.2, 0.5]),
                    b: new Float32Array([0.3, 0.6])
                };
                return values[name] ? { toArray: () => values[name] } : null;
            }
        };
        vi.mocked(tableFromIPC).mockResolvedValue(table as unknown as Table);

        const result = await parseCloudPointFrame(new ArrayBuffer(0), {
            channelId: 7,
            timestampNs: 'fallback'
        });

        expect(result.batch).toEqual({
            positions: new Float32Array([1, 2, 3, 4, 5, 6]),
            intensities: new Float32Array([0.25, 0.75]),
            colors: new Float32Array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]),
            count: 2
        });
        expect(result).toMatchObject({
            channelId: 7,
            timestampNs: '1788220800123000000',
            frameId: 'lidar',
            sourcePointCount: 2,
            bounds: { min: [1, 2, 3], max: [4, 5, 6] },
            channels: [{ channelId: 7, timestampNs: '1788220800123000000', frameId: 'lidar' }]
        });
    });

    it('rejects data without all coordinate columns', async () => {
        vi.mocked(tableFromIPC).mockResolvedValue({
            getChild: (name: string) => (name === 'x' ? { toArray: () => [1] } : null)
        } as unknown as Table);

        await expect(
            parseCloudPointFrame(new ArrayBuffer(0), { channelId: 7, timestampNs: '10' })
        ).rejects.toThrow('Point-cloud Arrow data must contain matching x, y, and z columns.');
    });
});
