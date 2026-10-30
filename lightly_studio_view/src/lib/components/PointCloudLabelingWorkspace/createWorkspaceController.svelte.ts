import { fromStore } from 'svelte/store';
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
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

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

    const accumulatePointClouds = useSessionStorage<boolean>(
        'lightlyStudio_pointCloudAccumulate',
        false
    );
    const accumulationRadius = useSessionStorage<number>(
        'lightlyStudio_pointCloudAccumulationRadius',
        1
    );
    const accumulating = fromStore(accumulatePointClouds);
    const radius = fromStore(accumulationRadius);

    workspace = createPointCloudWorkspaceContext(() => ({
        datasetId: getOptions().datasetId,
        sequenceId: getOptions().sequenceId,
        selectedLidarChannels: lidarSelection.selectedChannels ?? undefined,
        accumulationRadius: accumulating.current ? radius.current : 0,
        // Only the cloud query should depend on ticks; eager reads make the tick query
        // depend on its own result through every call to this input getter.
        get accumulationTickNumbers() {
            return workspace.ticks?.map((tick) => tick.seq_number) ?? [];
        },
        // The hash tick is 1-based; the transport tracks 0-based seq numbers.
        initialTick: (getOptions().tickNumber ?? 1) - 1,
        statusOverride: getOptions().status
    }));

    const presentation = useWorkspacePresentation();
    const fullscreen = useWorkspaceFullscreen();
    const cameraPane = useCameraPane();
    const playback = useWorkspacePlayback(
        () => workspace,
        getOptions,
        () => (accumulating.current ? radius.current : 0)
    );
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
        accumulation,
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
    const accumulation = {
        get accumulatePointClouds() {
            return accumulating.current;
        },
        get accumulationRadius() {
            return radius.current;
        },
        setAccumulatePointClouds: accumulatePointClouds.set,
        setAccumulationRadius: accumulationRadius.set
    };

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
        accumulation,
        lidarSelection,
        cameraSelection,
        get options() {
            return getOptions();
        },
        getLayout
    };
}
