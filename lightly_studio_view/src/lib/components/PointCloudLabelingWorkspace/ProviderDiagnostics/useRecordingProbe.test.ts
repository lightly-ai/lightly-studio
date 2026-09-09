import { describe, expect, it } from 'vitest';
import { canonicalCoordinateFrame } from '../domain';
import type { RecordingSession } from '../provider';
import { describeRecording, supportedChannel } from './useRecordingProbe.svelte';

const lidar = {
    channelId: 7,
    topic: '/livox/lidar_rear_left/self_filtered',
    schema: 'sensor_msgs/msg/PointCloud2',
    supported: true,
    messageCount: '1315'
};
const tf = {
    channelId: 8,
    topic: '/tf',
    schema: 'tf2_msgs/msg/TFMessage',
    supported: false,
    messageCount: '41632'
};

function session(metadata: Partial<RecordingSession['metadata']> = {}): RecordingSession {
    return {
        source: {
            recordingId: 'sample-1',
            version: 'rev-1',
            url: '/mcap/media/sample-1',
            sizeBytes: '898890680',
            coordinateFrame: canonicalCoordinateFrame('lidar'),
            logClockId: 'log',
            publishClockId: 'publish'
        },
        metadata: {
            topics: [tf, lidar],
            firstLogTimeNs: '1785698974144734233',
            lastLogTimeNs: '1785699105644734233',
            ...metadata
        },
        listFrames: async () => [],
        readFrame: async () => {
            throw new Error('not used');
        },
        dispose: () => undefined
    };
}

describe('supportedChannel', () => {
    it('picks the channel the browser can decode, whatever its order', () => {
        expect(supportedChannel(session()).topic).toBe('/livox/lidar_rear_left/self_filtered');
    });

    it('rejects a recording with no decodable channel', () => {
        expect(() => supportedChannel(session({ topics: [tf] }))).toThrow(/PointCloud2/);
    });

    it('rejects a recording with no time bounds to list within', () => {
        expect(() => supportedChannel(session({ firstLogTimeNs: null }))).toThrow(/PointCloud2/);
    });
});

describe('describeRecording', () => {
    it('derives the timeline length and the channel frame rate', () => {
        const recording = describeRecording(session());

        expect(recording.durationSeconds).toBeCloseTo(131.5, 3);
        expect(recording.frameRateHz).toBeCloseTo(10.0, 1);
        expect(recording.topic).toBe('/livox/lidar_rear_left/self_filtered');
        expect(recording.sizeBytes).toBe('898890680');
    });

    it('reports no rate when the recording counts no messages', () => {
        const recording = describeRecording(
            session({ topics: [{ ...lidar, messageCount: null }] })
        );

        expect(recording.frameRateHz).toBeNull();
        expect(recording.durationSeconds).toBeCloseTo(131.5, 3);
    });

    it('reports no timeline when the recording has no bounds', () => {
        const recording = describeRecording(session({ firstLogTimeNs: null }));

        expect(recording.durationSeconds).toBe(0);
        expect(recording.frameRateHz).toBeNull();
    });
});
