import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import PointCloudLabelingWorkspace from './PointCloudLabelingWorkspace.svelte';

describe('PointCloudLabelingWorkspace', () => {
    it('renders the chrome and the empty state by default', () => {
        render(PointCloudLabelingWorkspace, {
            props: { sampleId: 'sample-1', onExit: vi.fn() }
        });

        expect(screen.getByTestId('point-cloud-labeling-workspace')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-header')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-filter-bar')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-tool-rail')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-projection-strip')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-frame-timeline')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-annotation-panel')).toBeInTheDocument();
        expect(screen.getByTestId('workspace-status-panel')).toHaveAttribute(
            'data-status',
            'empty'
        );
        expect(screen.queryByTestId('workspace-scene-viewport')).not.toBeInTheDocument();
    });

    it('renders the source breadcrumb when a path is given', () => {
        render(PointCloudLabelingWorkspace, {
            props: {
                sampleId: 'sample-1',
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
            props: { sampleId: 'sample-1', onExit: vi.fn() }
        });

        expect(screen.queryByTestId('workspace-breadcrumb')).not.toBeInTheDocument();
        expect(screen.getByTestId('workspace-header')).toHaveTextContent('sample-1');
    });

    it('shows the unsupported state and does not render the panel layout', () => {
        render(PointCloudLabelingWorkspace, {
            props: { sampleId: 'sample-1', status: 'unsupported', onExit: vi.fn() }
        });

        expect(screen.getByTestId('workspace-status-panel')).toHaveAttribute(
            'data-status',
            'unsupported'
        );
        expect(screen.queryByTestId('workspace-projection-strip')).not.toBeInTheDocument();
        expect(screen.queryByTestId('workspace-annotation-panel')).not.toBeInTheDocument();
    });

    it('shows a recoverable error state with a retry action', async () => {
        const onRetry = vi.fn();
        render(PointCloudLabelingWorkspace, {
            props: { sampleId: 'sample-1', status: 'error', onExit: vi.fn(), onRetry }
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
            props: { sampleId: 'sample-1', onExit }
        });

        screen.getByRole('button', { name: /close labeling workspace/i }).click();
        expect(onExit).toHaveBeenCalledOnce();
    });
});
