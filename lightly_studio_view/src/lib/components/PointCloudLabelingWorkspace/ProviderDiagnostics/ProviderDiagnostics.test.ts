import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import ProviderDiagnostics from './ProviderDiagnostics.svelte';
import type { ProbeResult } from './providerProbe';

const { probeFirstFrame } = vi.hoisted(() => ({ probeFirstFrame: vi.fn() }));
vi.mock('./providerProbe', () => ({ probeFirstFrame }));

const result: ProbeResult = {
    sizeBytes: '942817280',
    version: 'rev-1',
    topics: [
        {
            channelId: 7,
            topic: '/lidar/points',
            schema: 'sensor_msgs/msg/PointCloud2',
            supported: true,
            messageCount: '900'
        },
        {
            channelId: 8,
            topic: '/imu',
            schema: 'sensor_msgs/msg/Imu',
            supported: false,
            messageCount: '90'
        }
    ],
    firstLogTimeNs: '1789000000000000000',
    lastLogTimeNs: '1789000000000000900',
    frameCount: 900,
    truncated: false,
    pointCount: 9000,
    sourcePointCount: 9000,
    frameId: 'frame-1',
    logTimeNs: '1789000000000000001'
};

describe('ProviderDiagnostics', () => {
    it('reports what the provider read', async () => {
        probeFirstFrame.mockResolvedValue(result);

        render(ProviderDiagnostics, { props: { sampleId: 'sample-1' } });

        expect(await screen.findByText('899.1 MB')).toBeInTheDocument();
        expect(screen.getByText('9,000 of 9,000')).toBeInTheDocument();
        expect(screen.getByText('/lidar/points')).toBeInTheDocument();
        expect(screen.getByText('/imu')).toBeInTheDocument();
        expect(screen.getByText('1789000000000000001')).toBeInTheDocument();
        expect(probeFirstFrame).toHaveBeenCalledWith(
            'sample-1',
            '/mcap/media/sample-1',
            expect.anything()
        );
    });

    it('shows why reading the recording failed', async () => {
        probeFirstFrame.mockRejectedValue(new Error('Recording access was denied.'));

        render(ProviderDiagnostics, { props: { sampleId: 'sample-1' } });

        expect(await screen.findByTestId('provider-diagnostics-error')).toHaveTextContent(
            'Recording access was denied.'
        );
    });

    it('reports progress phases and timings while reading', async () => {
        probeFirstFrame.mockImplementation(
            async (
                _sampleId: string,
                _url: string,
                callbacks: {
                    onPhase: (phase: string) => void;
                    onTelemetry: (event: { operation: string; durationMs: number }) => void;
                }
            ) => {
                callbacks.onPhase('indexing');
                callbacks.onTelemetry({ operation: 'decode', durationMs: 12.34 });
                return result;
            }
        );

        render(ProviderDiagnostics, { props: { sampleId: 'sample-1' } });

        expect(await screen.findByText('decode')).toBeInTheDocument();
        expect(screen.getByText(/12\.3 ms/)).toBeInTheDocument();
    });
});
