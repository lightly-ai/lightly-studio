import { createPointCloudWorkspaceContext } from './provider/createPointCloudWorkspaceContext';
import type { PointCloudWorkspaceContext } from './provider/types';
import type { WorkspaceOptions } from './workspaceOptions';
import type { PointCloudWorkspaceLayoutState } from './pointCloudWorkspaceLayoutContext.svelte';
import { useChannelSelection } from './useChannelSelection.svelte';
import { useWorkspacePresentation } from './useWorkspacePresentation/useWorkspacePresentation.svelte';
import { useWorkspacePlayback } from './useWorkspacePlayback/useWorkspacePlayback.svelte';
import { useWorkspaceSceneData } from './useWorkspaceSceneData/useWorkspaceSceneData.svelte';
import { useWorkspaceEditing } from './useWorkspaceEditing/useWorkspaceEditing.svelte';
import { useWorkspaceFullscreen } from './useWorkspaceFullscreen/useWorkspaceFullscreen.svelte';
import { useCameraPane } from './useCameraPane/useCameraPane.svelte';

/** Composes focused workspace controllers and projects their state for scene consumers. */
export function createWorkspaceController(getOptions: () => WorkspaceOptions) {
    let workspace = $state<PointCloudWorkspaceContext>({} as PointCloudWorkspaceContext);
    const lidarSelection = useChannelSelection({
        getChannels: () => workspace.lidarChannels,
        getResetKey: () => getOptions().sequenceId
    });
    const cameraSelection = useChannelSelection({
        getChannels: () => workspace.cameraChannels,
        getResetKey: () => getOptions().sequenceId
    });

    workspace = createPointCloudWorkspaceContext(() => ({
        datasetId: getOptions().datasetId,
        sequenceId: getOptions().sequenceId,
        selectedLidarChannels: lidarSelection.selectedChannels ?? undefined,
        // The hash tick is 1-based; the transport tracks 0-based seq numbers.
        initialTick: (getOptions().tickNumber ?? 1) - 1,
        statusOverride: getOptions().status
    }));

    const presentation = useWorkspacePresentation();
    const fullscreen = useWorkspaceFullscreen();
    const cameraPane = useCameraPane();
    const playback = useWorkspacePlayback(() => workspace, getOptions);
    const data = useWorkspaceSceneData(() => workspace, getOptions);
    const editing = useWorkspaceEditing(
        () => workspace,
        getOptions,
        () => data,
        () => presentation.isEditingMode
    );
    const getLayout = (): PointCloudWorkspaceLayoutState => ({
        workspace,
        datasetId: getOptions().datasetId,
        sequenceId: getOptions().sequenceId,
        sceneFrame: data.snapshot?.frame,
        cameraBatch: data.currentSnapshot?.frame.batch,
        fitKey: data.snapshot?.fitKey,
        sceneCuboids: data.cuboids,
        snapshotAnnotations: data.snapshotAnnotations,
        annotationClasses: data.annotationClasses,
        annotationSources: data.annotationSources,
        transforms: editing.transforms,
        activeTool: editing.activeTool,
        effectiveTool: editing.effectiveTool,
        isEditingMode: presentation.isEditingMode,
        showOrthographicViews: presentation.showOrthographicViews,
        pointSize: presentation.pointSize,
        showNavigationHelpers: presentation.showNavigationHelpers,
        showAnnotationTooltips: presentation.showAnnotationTooltips,
        colorMode: presentation.colorMode,
        selectedCuboidId: editing.selectedCuboidId,
        hoveredCuboidId: editing.hoveredCuboidId,
        selectedCameraChannelIds: cameraSelection.selectedChannelIds,
        cameraStripCollapsed: cameraPane.collapsed,
        bufferEntireSequence: playback.bufferEntireSequence,
        bufferedRanges: playback.bufferedRanges,
        onCameraStripCollapsedChange: cameraPane.setCollapsed,
        onToggleOrthographicProjections: presentation.toggleOrthographicProjections,
        onPointSizeChange: presentation.setPointSize,
        onToggleNavigationHelpers: presentation.setShowNavigationHelpers,
        onToggleAnnotationTooltips: presentation.setShowAnnotationTooltips,
        onToolChange: (tool) => {
            editing.activeTool = tool;
        },
        onSelect: (id) => {
            editing.selectedCuboidId = id;
        },
        onHover: (id) => {
            editing.hoveredCuboidId = id;
        },
        onCreateCuboid: editing.handleCreateCuboid,
        onPreviousFrame: playback.goToPreviousFrame,
        onNextFrame: playback.goToNextFrame,
        onPlayToggle: playback.togglePlayback,
        onPlaybackIntervalChange: workspace.setPlaybackIntervalMs,
        onSelectTick: playback.handleSelectTick,
        onSeekStart: playback.handleSeekStart,
        onSeekEnd: playback.handleSeekEnd,
        onBufferEntireSequenceChange: playback.setBufferEntireSequence,
        onPreviousSequence: getOptions().onPreviousSequence,
        onNextSequence: getOptions().onNextSequence
    });
    return {
        get workspace() {
            return workspace;
        },
        presentation,
        fullscreen,
        cameraPane,
        playback,
        data,
        editing,
        lidarSelection,
        cameraSelection,
        get options() {
            return getOptions();
        },
        getLayout
    };
}
