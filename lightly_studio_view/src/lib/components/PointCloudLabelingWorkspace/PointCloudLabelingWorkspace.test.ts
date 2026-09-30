import { beforeAll, describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import PointCloudLabelingWorkspace from './PointCloudLabelingWorkspace.svelte';

// The workspace mounts the camera projection strip, which reads the tick details
// query; stub it so the chrome renders without a live TanStack query client.
vi.mock('$lib/hooks/useTickDetails/useTickDetails', () => ({
    useTickDetails: () => ({ tickDetails: { data: undefined } })
}));

vi.mock('$lib/hooks/useCloudPointFrame/useCloudPointFrame.svelte', () => ({
    useCloudPointFrame: () => ({
        query: { data: undefined, isLoading: false, isError: false, refetch: vi.fn() }
    })
}));

vi.mock('$lib/hooks/useMcapSequenceTicks/useMcapSequenceTicks.svelte', () => ({
    useMcapSequenceTicks: () => ({
        ticks: {
            data: {
                ticks: [
                    { seq_number: 0, timestamp_ns: 1000 },
                    { seq_number: 1, timestamp_ns: 2000 }
                ]
            }
        },
        refetch: vi.fn()
    })
}));

vi.mock('$lib/hooks/useMcapSequenceSummary/useMcapSequenceSummary', () => ({
    useMcapSequenceSummary: () => ({
        summary: {
            data: {
                lidar_channels: [
                    {
                        channel_id: 1,
                        group_component_name: 'lidar_top',
                        group_component_index: 0
                    }
                ],
                camera_channels: []
            },
            isLoading: false,
            isError: false
        },
        refetch: vi.fn()
    })
}));

const defaultProps = { sampleId: 'sample-1', datasetId: 'dataset-1', sequenceId: 'sequence-1' };

describe('PointCloudLabelingWorkspace', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('renders the chrome and the empty state by default', () => {
        render(PointCloudLabelingWorkspace, {
            props: {
                ...defaultProps,
                onExit: vi.fn()
            }
        });

        expect(screen.getByTestId('point-cloud-labeling-workspace')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-header')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-filter-bar')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-tool-rail')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-projection-strip')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-frame-timeline')).toBeInTheDocument();
        expect(screen.getByText('Frame 1 / 2')).toBeInTheDocument();
        expect(screen.getByText('lidar_top')).toBeInTheDocument();
        expect(screen.getByTestId('point-cloud-right-side-panel')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-status-panel')).toHaveAttribute(
            'data-status',
            'empty'
        );
        expect(screen.queryByTestId('workspace-scene-viewport')).not.toBeInTheDocument();
    });

    it('renders the source breadcrumb when a path is given', () => {
        render(PointCloudLabelingWorkspace, {
            props: {
                ...defaultProps,
                sourcePath: [
                    { label: 'Home', href: '/datasets/d1/mcap/d1' },
                    { label: 'Recordings', href: '/datasets/d1/mcap/c1' },
                    { label: 'sample-1' }
                ],
                onExit: vi.fn()
            }
        });

        const breadcrumb = screen.getByTestId('workspace-breadcrumb');
        expect(breadcrumb).toBeInTheDocument();
        expect(breadcrumb).toHaveTextContent('Recordings');
        expect(breadcrumb).toHaveTextContent('sample-1');
    });

    it('falls back to the sample id when no source path is given', () => {
        render(PointCloudLabelingWorkspace, {
            props: {
                ...defaultProps,
                onExit: vi.fn()
            }
        });

        expect(screen.queryByTestId('workspace-breadcrumb')).not.toBeInTheDocument();
        expect(screen.getByTestId('workspace-header')).toHaveTextContent('sample-1');
    });

    it('shows the unsupported state and does not render the panel layout', () => {
        render(PointCloudLabelingWorkspace, {
            props: {
                ...defaultProps,
                status: 'unsupported',
                onExit: vi.fn()
            }
        });

        expect(screen.getByTestId('workspace-status-panel')).toHaveAttribute(
            'data-status',
            'unsupported'
        );
        expect(screen.queryByTestId('workspace-projection-strip')).not.toBeInTheDocument();
        expect(screen.queryByTestId('point-cloud-right-side-panel')).not.toBeInTheDocument();
    });

    it('shows a recoverable error state with a retry action', async () => {
        const onRetry = vi.fn();
        render(PointCloudLabelingWorkspace, {
            props: {
                ...defaultProps,
                status: 'error',
                onExit: vi.fn(),
                onRetry
            }
        });

        expect(screen.getByTestId('workspace-status-panel')).toHaveAttribute(
            'data-status',
            'error'
        );
        screen.getByRole('button', { name: /retry/i }).click();
        expect(onRetry).toHaveBeenCalledOnce();
    });

    it('calls onExit when the close button is clicked', () => {
        const onExit = vi.fn();
        render(PointCloudLabelingWorkspace, {
            props: {
                ...defaultProps,
                onExit
            }
        });

        screen.getByRole('button', { name: /close labeling workspace/i }).click();
        expect(onExit).toHaveBeenCalledOnce();
    });

    it('navigates through the loaded ticks from the timeline controls', async () => {
        const user = userEvent.setup();
        const onTickChange = vi.fn();
        render(PointCloudLabelingWorkspace, {
            props: {
                ...defaultProps,
                onTickChange
            }
        });

        await user.click(screen.getByRole('button', { name: 'Next frame' }));
        expect(screen.getByText('Frame 2 / 2')).toBeInTheDocument();
        expect(onTickChange).toHaveBeenLastCalledWith(2);

        await user.click(screen.getByRole('button', { name: 'Previous frame' }));
        expect(screen.getByText('Frame 1 / 2')).toBeInTheDocument();
        expect(onTickChange).toHaveBeenLastCalledWith(1);
    });

    it('updates the active frame when the route tick changes', async () => {
        const props = {
            ...defaultProps,
            tickNumber: 1
        };
        const { rerender } = render(PointCloudLabelingWorkspace, { props });

        await rerender({ ...props, tickNumber: 2 });

        expect(screen.getByText('Frame 2 / 2')).toBeInTheDocument();
    });

    it.each([
        { datasetId: 'dataset-2', sequenceId: 'sequence-1' },
        { datasetId: 'dataset-1', sequenceId: 'sequence-2' }
    ])(
        'resets the LiDAR selection when the source changes to $datasetId/$sequenceId',
        async (next) => {
            const user = userEvent.setup();
            const props = {
                ...defaultProps,
                onExit: vi.fn()
            };
            const { rerender } = render(PointCloudLabelingWorkspace, { props });

            await user.click(screen.getByTestId('workspace-lidar-select'));
            await user.click(screen.getByTestId('workspace-lidar-select-1'));
            expect(screen.getByTestId('workspace-lidar-select')).not.toHaveTextContent(':');

            await rerender({ ...props, ...next });

            await waitFor(() =>
                expect(screen.getByTestId('workspace-lidar-select')).toHaveTextContent(
                    'Lidar: lidar_top'
                )
            );
        }
    );
});
