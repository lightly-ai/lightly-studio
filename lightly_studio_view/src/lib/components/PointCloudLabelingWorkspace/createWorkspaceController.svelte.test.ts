import { render, screen, waitFor } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/svelte-query';
import { flushSync } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import Harness from './WorkspaceControllerHarness.svelte';

vi.mock('$lib/hooks/useTickDetails/useTickDetails', () => ({
    useTickDetails: () => ({ tickDetails: { data: undefined } })
}));
vi.mock('$lib/hooks/useTickData/getTickDataOptions', () => ({
    getTickDataOptions: () => ({
        queryKey: ['tick-data'],
        queryFn: async () => ({
            pointClouds: [
                {
                    batch: {
                        positions: new Float32Array(3),
                        intensities: new Float32Array(1),
                        count: 1
                    },
                    channelId: 1,
                    timestampNs: '10',
                    frameId: 'map',
                    sourcePointCount: 1,
                    bounds: null,
                    channels: [{ channelId: 1, timestampNs: '10', frameId: 'map' }]
                }
            ],
            cameraFrames: {}
        })
    })
}));
vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    getSummaryOptions: () => ({
        queryKey: ['summary'],
        queryFn: async () => ({ lidar_channels: [], camera_channels: [], reference_frames: [] })
    }),
    getTicksOptions: () => ({
        queryKey: ['ticks'],
        queryFn: async () => ({ ticks: [{ seq_number: 0, timestamp_ns: 10 }] })
    })
}));
vi.mock('./useWorkspacePresentation/useWorkspacePresentation.svelte', () => ({
    useWorkspacePresentation: () => ({})
}));
vi.mock('./useWorkspaceFullscreen/useWorkspaceFullscreen.svelte', () => ({
    useWorkspaceFullscreen: () => ({})
}));
vi.mock('./useCameraPane/useCameraPane.svelte', () => ({ useCameraPane: () => ({}) }));
vi.mock('./useWorkspacePlayback/useWorkspacePlayback.svelte', () => ({
    useWorkspacePlayback: () => ({})
}));
vi.mock('./useWorkspaceSceneData/useWorkspaceSceneData.svelte', () => ({
    useWorkspaceSceneData: () => ({})
}));
vi.mock('./useWorkspaceEditing/useWorkspaceEditing.svelte', () => ({
    useWorkspaceEditing: () => ({})
}));

describe('workspace query dependencies', () => {
    it('loads and updates sequence ticks without a reactive update loop', async () => {
        const client = new QueryClient({
            defaultOptions: { queries: { staleTime: Infinity, retry: false } }
        });
        const { unmount } = render(Harness, { client });
        try {
            flushSync();
            await waitFor(() => expect(screen.getByText('Ticks: 1')).toBeInTheDocument());
            await waitFor(() => expect(screen.getByText('Points: 1')).toBeInTheDocument());

            client.setQueryData(['ticks'], {
                ticks: [
                    { seq_number: 0, timestamp_ns: 10 },
                    { seq_number: 1, timestamp_ns: 20 }
                ]
            });
            flushSync();
            expect(screen.getByText('Ticks: 2')).toBeInTheDocument();
        } finally {
            unmount();
            client.clear();
        }
    });
});
