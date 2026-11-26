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
import { usePanelVisibility } from './usePanelVisibility/usePanelVisibility.svelte';
import { useCollapsiblePane } from './useCollapsiblePane/useCollapsiblePane.svelte';
import { useCuboidTargetSource } from './useCuboidTargetSource';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { isSelectedCuboidHidden, useAnnotationVisibility } from './useAnnotationVisibility';

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
    const cameraPane = useCollapsiblePane('lightlyStudio_pointCloudCameraStripCollapsed');
    const detailsPane = useCollapsiblePane('lightlyStudio_pointCloudDetailsCollapsed');
    const objectTracksPanel = usePanelVisibility('lightlyStudio_pointCloudObjectTracksShown', true);
    const tagTracksPanel = usePanelVisibility('lightlyStudio_pointCloudFrameTagTracksShown', false);
    const playback = useWorkspacePlayback(
        () => workspace,
        getOptions,
        () => (accumulating.current ? radius.current : 0)
    );
    const data = useWorkspaceSceneData(() => workspace, getOptions);
    const targetSource = useCuboidTargetSource({
        getCollectionId: () => getOptions().annotationSourceCollectionId,
        getSourceNames: () => data.annotationSourceNames,
        getIsError: () => data.annotationSourcesError
    });
    const editing = useWorkspaceEditing(
        () => workspace,
        getOptions,
        () => data,
        () => presentation.isEditingMode,
        () => targetSource
    );
    const visibility = useAnnotationVisibility(() => getOptions().sequenceId);
    // A hidden cuboid cannot be seen, so it must not stay selected. This covers every way to
    // select one: the panel, the timeline, and a new cuboid in a hidden source.
    $effect(() => {
        const { selectedCuboidId, annotations } = editing;
        if (isSelectedCuboidHidden(selectedCuboidId, annotations, visibility.isCuboidHidden)) {
            editing.selectedCuboidId = null;
        }
    });
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
        cuboidTarget: targetSource,
        transforms: editing.transforms,
        isCuboidHidden: visibility.isCuboidHidden,
        isTickAnnotationHidden: visibility.isTickAnnotationHidden,
        activeTool: editing.activeTool,
        effectiveTool: editing.effectiveTool,
        isEditingMode: presentation.isEditingMode,
        showOrthographicViews: presentation.showOrthographicViews,
        pointSize: presentation.pointSize,
        showNavigationHelpers: presentation.showNavigationHelpers,
        accumulation,
        colorMode: presentation.colorMode,
        selectedCuboidId: editing.selectedCuboidId,
        hoveredCuboidId: editing.hoveredCuboidId,
        // The draft target does not clear its highlight on teardown, so it ends with the tool.
        draftCuboid: editing.effectiveTool === 'create-cuboid' ? editing.draftCuboid : null,
        selectedCameraChannelIds: cameraSelection.selectedChannelIds,
        cameraStripCollapsed: cameraPane.collapsed,
        bufferEntireSequence: playback.bufferEntireSequence,
        bufferedRanges: playback.bufferedRanges,
        bufferStatus: playback.bufferStatus,
        onCameraStripCollapsedChange: cameraPane.setCollapsed,
        onToggleOrthographicProjections: presentation.toggleOrthographicProjections,
        onPointSizeChange: presentation.setPointSize,
        onToggleNavigationHelpers: presentation.setShowNavigationHelpers,
        onToolChange: (tool) => {
            editing.activeTool = tool;
        },
        onSelect: (id) => {
            editing.selectedCuboidId = id;
        },
        onHover: (id) => {
            editing.hoveredCuboidId = id;
        },
        onCuboidDraftChange: (box) => {
            editing.draftCuboid = box;
        },
        onCreateCuboid: editing.handleCreateCuboid,
        isAddingTrack: editing.isAddingTrack,
        onToggleAddTrack: editing.toggleAddTrack,
        onExtendTrack: editing.handleExtendTrack,
        onDeleteTrack: editing.handleDeleteTrack,
        onStartTrack: editing.handleStartTrack,
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
        detailsPane,
        objectTracksPanel,
        tagTracksPanel,
        playback,
        data,
        targetSource,
        editing,
        visibility,
        accumulation,
        lidarSelection,
        cameraSelection,
        get options() {
            return getOptions();
        },
        getLayout
    };
}
