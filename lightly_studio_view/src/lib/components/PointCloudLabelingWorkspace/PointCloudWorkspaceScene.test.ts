import { fireEvent, render, screen, within } from '@testing-library/svelte';
import { expect, it, vi } from 'vitest';
import type { PointCloudWorkspaceLayoutState } from './pointCloudWorkspaceLayoutContext.svelte';
import WorkspaceSceneProviderHarness from './WorkspaceSceneProviderHarness.svelte';
import { createCuboidTransformState } from './CuboidLayer/cuboidTransformState';

vi.mock('./SceneViewport/SceneViewport.svelte', async () => ({
    default: (await import('./SceneViewport/SceneViewportContentHarness.svelte')).default
}));

type Props = PointCloudWorkspaceLayoutState;
const defaultProps: Props = {
    workspace: {
        status: 'ready',
        tickDetails: { isError: false },
        cloudPointFrame: { isError: false }
    } as Props['workspace'],
    sceneFrame: {
        batch: { positions: new Float32Array(), intensities: new Float32Array(), count: 0 },
        bounds: null
    } as Props['sceneFrame'],
    sceneCuboids: [],
    datasetId: 'dataset',
    sequenceId: 'sequence',
    snapshotAnnotations: [],
    selectedCameraChannelIds: [],
    cameraStripCollapsed: false,
    bufferEntireSequence: false,
    bufferedRanges: [],
    onCameraStripCollapsedChange: vi.fn(),
    onBufferEntireSequenceChange: vi.fn(),
    onPlayToggle: vi.fn(),
    onPlaybackIntervalChange: vi.fn(),
    onSelectTick: vi.fn(),
    onSeekStart: vi.fn(),
    onSeekEnd: vi.fn(),
    annotationClasses: [],
    annotationSources: [],
    transforms: createCuboidTransformState({ onTransform: async () => true }),
    activeTool: 'select',
    effectiveTool: 'select',
    isEditingMode: true,
    showOrthographicViews: true,
    pointSize: 2,
    showNavigationHelpers: true,
    showAnnotationTooltips: true,
    colorMode: 'intensity',
    selectedCuboidId: null,
    hoveredCuboidId: null,
    onToggleOrthographicProjections: vi.fn(),
    onPointSizeChange: vi.fn(),
    onToggleNavigationHelpers: vi.fn(),
    onToggleAnnotationTooltips: vi.fn(),
    onToolChange: vi.fn(),
    onSelect: vi.fn(),
    onHover: vi.fn(),
    onCreateCuboid: vi.fn(),
    onPreviousFrame: vi.fn(),
    onNextFrame: vi.fn()
};

it('keeps the toolbar in the main viewport and restores all views without remounting them', async () => {
    render(WorkspaceSceneProviderHarness, { props: { state: defaultProps } });
    const main = screen.getByRole('region', { name: 'perspective' });
    expect(main.contains(screen.getByTestId('workspace-tool-rail'))).toBe(true);
    const viewports = screen.getAllByTestId('scene-viewport-instance');

    for (const label of ['Top', 'Side', 'Front', '3D scene']) {
        await fireEvent.click(screen.getByRole('button', { name: `Expand ${label} view` }));
        expect(screen.getAllByRole('region')).toHaveLength(1);
        expect(screen.getAllByTestId('scene-viewport-instance')).toEqual(viewports);
        await fireEvent.click(screen.getByRole('button', { name: 'Restore views' }));
        expect(screen.getAllByRole('region')).toHaveLength(4);
    }
});

it('shares navigation in both directions, preserves scale through expansion, and resets on a new fit key', async () => {
    const { rerender } = render(WorkspaceSceneProviderHarness, {
        props: { state: { ...defaultProps, fitKey: 'sequence/map' } }
    });
    for (const [cameraMode, scale] of [
        ['perspective', '0.05'],
        ['top', '0.025']
    ]) {
        await fireEvent.click(screen.getByRole('button', { name: `Navigate ${cameraMode}` }));
        for (const mode of ['perspective', 'top', 'side', 'front']) {
            expect(screen.getByLabelText(`${mode} scale`)).toHaveTextContent(scale);
        }
    }
    await fireEvent.click(screen.getByRole('button', { name: 'Expand Front view' }));
    expect(screen.getByLabelText('front scale')).toHaveTextContent('0.025');
    await fireEvent.click(screen.getByRole('button', { name: 'Restore views' }));
    await rerender({ state: { ...defaultProps, fitKey: 'sequence/sensor' } });
    for (const mode of ['perspective', 'top', 'side', 'front']) {
        expect(screen.getByLabelText(`${mode} scale`)).toHaveTextContent('unset');
    }
});

it('restores the main viewport when projections are disabled while one is expanded', async () => {
    const { rerender } = render(WorkspaceSceneProviderHarness, { props: { state: defaultProps } });
    await fireEvent.click(screen.getByRole('button', { name: 'Expand Top view' }));
    await rerender({ state: { ...defaultProps, showOrthographicViews: false } });
    expect(screen.getByRole('region', { name: 'perspective' })).toBeVisible();
    expect(screen.queryByRole('region', { name: 'top' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Restore views' })).not.toBeInTheDocument();
});

it('isolates camera state between separate workspace providers', async () => {
    const first = render(WorkspaceSceneProviderHarness, { props: { state: defaultProps } });
    const second = render(WorkspaceSceneProviderHarness, { props: { state: defaultProps } });
    await fireEvent.click(within(first.container).getByRole('button', { name: 'Navigate top' }));
    expect(within(first.container).getByLabelText('perspective scale')).toHaveTextContent('0.025');
    expect(within(second.container).getByLabelText('perspective scale')).toHaveTextContent('unset');
});
