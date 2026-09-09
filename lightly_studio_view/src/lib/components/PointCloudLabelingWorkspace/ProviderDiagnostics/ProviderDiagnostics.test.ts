import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { canonicalCoordinateFrame, createPointCloudFrame } from '../domain';
import ProviderDiagnostics from './ProviderDiagnostics.svelte';

const { useRecordingProbe } = vi.hoisted(() => ({ useRecordingProbe: vi.fn() }));
vi.mock('./useRecordingProbe.svelte', () => ({ useRecordingProbe }));

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

function probe(overrides: Record<string, unknown> = {}) {
    const state = {
        phase: 'ready',
        failure: undefined,
        failureDetail: undefined,
        telemetry: [{ operation: 'decode', durationMs: 8.53, bytesRead: 457728 }],
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
        atLimit: true,
        position: 0,
        frame: frame('1785698974144734233'),
        isLoading: false,
        step: vi.fn((next: number) => {
            state.position = next;
            state.frame = frame(String(1785698974144734233n + BigInt(next)));
        }),
        ...overrides
    };
    useRecordingProbe.mockReturnValue(state);
    return state;
}

describe('ProviderDiagnostics', () => {
    it('reports the recording and the frame in view', () => {
        probe();

        render(ProviderDiagnostics, { props: { sampleId: 'sample-1' } });

        expect(screen.getByText('857.2 MB')).toBeInTheDocument();
        expect(screen.getByText('131.5 s · 10.0 Hz')).toBeInTheDocument();
        expect(screen.getByText('9 of 11,053')).toBeInTheDocument();
        expect(screen.getByText('1785698974144734233')).toBeInTheDocument();
        expect(screen.getByText('/tf')).toBeInTheDocument();
        expect(screen.getByTestId('provider-frame-position')).toHaveTextContent('1 / 5+');
        expect(screen.getByText(/8\.5 ms/)).toBeInTheDocument();
        expect(screen.getByText(/447 KB/)).toBeInTheDocument();
    });

    it('steps to the next frame on request', async () => {
        const state = probe();
        render(ProviderDiagnostics, { props: { sampleId: 'sample-1' } });

        await userEvent.click(screen.getByLabelText('Next frame'));

        expect(state.step).toHaveBeenCalledWith(1);
    });

    it('cannot step past either end of the listed window', () => {
        probe({ frameCount: 1, atLimit: false });

        render(ProviderDiagnostics, { props: { sampleId: 'sample-1' } });

        expect(screen.getByLabelText('Previous frame')).toBeDisabled();
        expect(screen.getByLabelText('Next frame')).toBeDisabled();
    });

    it('shows why reading the recording failed, with the cause', () => {
        probe({
            failure: 'The MCAP recording could not be read or decoded.',
            failureDetail: "TypeError: Failed to execute 'fetch': Illegal invocation"
        });

        render(ProviderDiagnostics, { props: { sampleId: 'sample-1' } });

        expect(screen.getByTestId('provider-diagnostics-error')).toHaveTextContent(
            'could not be read or decoded'
        );
        expect(screen.getByTestId('provider-diagnostics-detail')).toHaveTextContent(
            'Illegal invocation'
        );
    });
});
