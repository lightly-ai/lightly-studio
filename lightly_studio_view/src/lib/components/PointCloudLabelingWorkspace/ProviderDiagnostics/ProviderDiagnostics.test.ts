import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { canonicalCoordinateFrame, createPointCloudFrame } from '../domain';
import ProviderDiagnostics from './ProviderDiagnostics.svelte';

function frame(logTimeNs: string) {
    return createPointCloudFrame({
        id: `frame-${logTimeNs}`,
        source: { recordingId: 'r', streamId: '7', messageId: logTimeNs, publishedAt: null },
        timestamp: { nanoseconds: logTimeNs, clockId: 'log' },
        coordinateFrame: canonicalCoordinateFrame('lidar'),
        sourcePointCount: 11053,
        positions: new Float32Array(9 * 3),
        cameras: []
    });
}

function state(overrides: Record<string, unknown> = {}) {
    const probe = {
        phase: 'ready',
        failure: undefined,
        failureDetail: undefined,
        telemetry: [{ operation: 'decode' as const, durationMs: 8.53, bytesRead: 457728 }],
        recording: {
            sizeBytes: '898890680',
            version: 'rev-1',
            topics: [
                {
                    channelId: 7,
                    topic: '/livox/lidar_rear_left/self_filtered',
                    schema: 'sensor_msgs/msg/PointCloud2',
                    supported: true,
                    messageCount: '1315'
                },
                {
                    channelId: 8,
                    topic: '/tf',
                    schema: 'tf2_msgs/msg/TFMessage',
                    supported: false,
                    messageCount: '41632'
                }
            ],
            topic: '/livox/lidar_rear_left/self_filtered',
            durationSeconds: 131.5,
            frameRateHz: 10.0
        },
        frameCount: 5,
        hasMore: true,
        position: 0,
        frame: frame('1785698974144734233'),
        isLoading: false,
        previous: vi.fn(),
        next: vi.fn(),
        ...overrides
    };
    return probe;
}

describe('ProviderDiagnostics', () => {
    it('reports the recording and the frame in view', () => {
        const probe = state();

        render(ProviderDiagnostics, { props: { probe } });

        expect(screen.getByText('857.2 MB')).toBeInTheDocument();
        expect(screen.getByText('131.5 s · 10.0 Hz')).toBeInTheDocument();
        expect(screen.getByText('9 of 11,053')).toBeInTheDocument();
        expect(screen.getByText('1785698974144734233')).toBeInTheDocument();
        expect(screen.getByText('/tf')).toBeInTheDocument();
        expect(screen.getByText(/8\.5 ms/)).toBeInTheDocument();
        expect(screen.getByText(/447 KB/)).toBeInTheDocument();
    });

    it('leaves frame navigation to the timeline', () => {
        const probe = state();

        render(ProviderDiagnostics, { props: { probe } });

        expect(screen.queryByLabelText('Next frame')).not.toBeInTheDocument();
    });

    it('shows why reading the recording failed, with the cause', () => {
        const probe = state({
            failure: 'The MCAP recording could not be read or decoded.',
            failureDetail: "TypeError: Failed to execute 'fetch': Illegal invocation"
        });

        render(ProviderDiagnostics, { props: { probe } });

        expect(screen.getByTestId('provider-diagnostics-error')).toHaveTextContent(
            'could not be read or decoded'
        );
        expect(screen.getByTestId('provider-diagnostics-detail')).toHaveTextContent(
            'Illegal invocation'
        );
    });
});
