import type { CuboidTarget } from './useCuboidTargetSource';
import type { CuboidBox } from '$lib/components/PointCloudLabelingWorkspace/CuboidDraft';
import { getContext, setContext } from 'svelte';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import type { ColorMode } from '$lib/components/PointCloudViewer';
import type { PointCloudWorkspaceContext } from './provider/types';
import type { AnnotationClass, AnnotationSource, CuboidAnnotation, WorkspaceTool } from './domain';
import type { createCuboidTransformState } from './CuboidLayer/cuboidTransformState';
import type { createWorkspaceController } from './createWorkspaceController.svelte';
import type { HistoryMode } from './workspaceOptions';
import type { PanelDock } from './PanelDockToggle';

/** Inclusive range of timeline ticks already available for playback. */
interface BufferRange {
    /** Inclusive zero-based index of the first buffered tick. */
    startIndex: number;
    /** Inclusive zero-based index of the last buffered tick. */
    endIndex: number;
}

/** Reactive scene data and actions shared by the workspace's layout subtree. */
export interface PointCloudWorkspaceLayoutState {
    /** Loaded sequence data and transport controls. */
    workspace: PointCloudWorkspaceContext;
    /** Dataset containing the displayed sequence. */
    datasetId: string;
    /** Sequence displayed by the labeling workspace. */
    sequenceId: string;
    /** Last complete point-cloud frame retained during tick transitions. */
    sceneFrame?: NonNullable<PointCloudWorkspaceContext['cloudPointFrame']['data']>;
    /** Current tick cloud for camera overlays; omitted while the tick is stale. */
    cameraBatch?: import('$lib/components/PointCloudViewer').PointBatch;
    /** Changes when the sequence or coordinate frame requires a new camera fit. */
    fitKey?: string;
    /** Cuboids filtered to the visible cloud coordinate frame. */
    sceneCuboids: readonly CuboidAnnotation[];
    /** Annotations belonging to the current complete tick snapshot. */
    snapshotAnnotations: readonly TickDetailView['annotations'][number][];
    /** Annotation classes and colors used to render cuboids. */
    annotationClasses: readonly AnnotationClass[];
    /** Available annotation sources for the active sequence. */
    annotationSources: readonly AnnotationSource[];
    /** The annotation source new cuboids go to. */
    cuboidTarget: CuboidTarget;
    /** Shared annotation transforms and their persistence actions. */
    transforms: ReturnType<typeof createCuboidTransformState>;
    /** True when the user hid the source or the track of the cuboid. */
    isCuboidHidden: (cuboid: CuboidAnnotation) => boolean;
    /** True when the user hid the source or the track of the tick annotation. */
    isTickAnnotationHidden: (annotation: TickDetailView['annotations'][number]) => boolean;
    /** Tool selected in the main scene toolbar. */
    activeTool: WorkspaceTool;
    /** Selected tool constrained by current editing permissions. */
    effectiveTool: WorkspaceTool;
    /** Whether annotation edits are permitted. */
    isEditingMode: boolean;
    /** Whether the Top, Side, and Front views are on screen: turned on and not collapsed. */
    showOrthographicViews: boolean;
    /** Where the orthographic views sit next to the 3D scene. */
    orthographicDock: PanelDock;
    /** Where the camera strip sits next to the scene column. */
    cameraStripDock: PanelDock;
    /** Screen-space point size in CSS pixels. */
    pointSize: number;
    /** Whether navigation buttons and shortcut hints are shown. */
    showNavigationHelpers: boolean;
    /** Accumulation preferences and actions for the scene settings. */
    accumulation?: ReturnType<typeof createWorkspaceController>['accumulation'];
    /** Strategy used to color the point cloud. */
    colorMode: Exclude<ColorMode, 'none'>;
    /** Changes how the points are colored. */
    onColorModeChange: (colorMode: Exclude<ColorMode, 'none'>) => void;
    /** Lidar channels currently shown in the scene. */
    selectedLidarChannelIds: number[];
    /** Toggles a lidar channel by its `channel_id`. */
    onToggleLidarChannel: (channelId: number) => void;
    /** Replaces the shown lidar channels. */
    onSetLidarChannels: (channelIds: number[]) => void;
    /** Selected cuboid identifier, or null. */
    selectedCuboidId: string | null;
    /** Hovered cuboid identifier, or null. */
    hoveredCuboidId: string | null;
    /** Region of the cuboid being drawn, or null; its points are highlighted in every viewport. */
    draftCuboid: CuboidBox | null;
    /** Camera channels currently visible in the strip. */
    selectedCameraChannelIds: number[];
    /** Toggles a camera channel by its `channel_id`. */
    onToggleCameraChannel: (channelId: number) => void;
    /** Replaces the shown camera channels. */
    onSetCameraChannels: (channelIds: number[]) => void;
    /** Whether the camera strip is reduced to its header. */
    cameraStripCollapsed: boolean;
    /** Camera shown in the enlarged camera dialog, or undefined when it is closed. */
    openCamera: string | undefined;
    /** Opens, switches, or closes the enlarged camera dialog. */
    onOpenCameraChange: (camera: string | undefined, historyMode: HistoryMode) => void;
    /** Whether buffering covers the complete sequence. */
    bufferEntireSequence: boolean;
    /** Inclusive tick ranges ready for playback. */
    bufferedRanges: readonly BufferRange[];
    /** Playback waiting state and recovery for failed background loads. */
    bufferStatus?: ReturnType<typeof createWorkspaceController>['playback']['bufferStatus'];
    /** Persists the collapsed state reported by the camera pane. */
    onCameraStripCollapsedChange: (collapsed: boolean) => void;
    /** Updates orthographic projection visibility. */
    onToggleOrthographicProjections: (show: boolean) => void | Promise<void>;
    /** Moves the orthographic views. */
    onOrthographicDockChange: (dock: PanelDock) => void;
    /** Moves the camera strip. */
    onCameraStripDockChange: (dock: PanelDock) => void;
    /** Updates the preferred point size. */
    onPointSizeChange: (value: number) => void;
    /** Updates navigation helper visibility. */
    onToggleNavigationHelpers: (show: boolean) => void;
    /** Selects the tool shared by all scene viewports. */
    onToolChange: (tool: WorkspaceTool) => void;
    /** Selects or clears the current cuboid. */
    onSelect: (annotationId: string | null) => void;
    /** Updates the cuboid shown by hover feedback. */
    onHover: (annotationId: string | null) => void;
    /** Updates the region of the cuboid being drawn. */
    onCuboidDraftChange: (box: CuboidBox | null) => void;
    /** Creates an annotation from a drawn box. */
    onCreateCuboid: (box: CuboidBox, selectClass?: boolean) => void | Promise<void>;
    /** Whether the next created cuboid also starts a new object track. */
    isAddingTrack: boolean;
    /** Arms or cancels creating a new object track with its first cuboid. */
    onToggleAddTrack: () => void;
    /** Extends a track onto the ticks from `startSeqNumber` to `endSeqNumber`. */
    onExtendTrack: (params: {
        trackId: string;
        annotationSourceId: string;
        startSeqNumber: number;
        endSeqNumber: number;
    }) => void | Promise<unknown>;
    /** Deletes a track with its cuboids; resolves to whether it was deleted. */
    onDeleteTrack: (params: {
        trackId: string;
        annotationSourceId: string;
        annotationIds: readonly string[];
    }) => Promise<boolean>;
    /** Starts an object track from an untracked cuboid. */
    onStartTrack: (annotationId: string) => void | Promise<unknown>;
    /** Navigates to the previous tick. */
    onPreviousFrame: () => void;
    /** Navigates to the next tick. */
    onNextFrame: () => void;
    /** Starts or pauses sequence playback. */
    onPlayToggle: () => void;
    /** Updates the playback frame interval in milliseconds. */
    onPlaybackIntervalChange: (intervalMs: number) => void;
    /** Seeks to the requested tick and updates the buffering window. */
    onSelectTick: (seqNumber: number) => void;
    /** Pauses playback while the timeline is being dragged. */
    onSeekStart: () => void;
    /** Restores playback after a timeline drag. */
    onSeekEnd: () => void;
    /** Updates the whole-sequence buffering preference. */
    onBufferEntireSequenceChange: (enabled: boolean) => void;
    /** Opens the previous sequence when available. */
    onPreviousSequence?: () => void;
    /** Opens the next sequence when available. */
    onNextSequence?: () => void;
}

const CONTEXT_KEY = Symbol('point-cloud-workspace-layout');

/** Scene-facing state and optional workspace shell controllers supplied by the provider. */
interface WorkspaceContext {
    /** Reads reactive scene data and actions. */
    getState: () => PointCloudWorkspaceLayoutState;
    /** Shell controllers, absent in isolated scene harnesses. */
    controller?: ReturnType<typeof createWorkspaceController>;
}

export function providePointCloudWorkspaceLayoutContext(
    getState: () => PointCloudWorkspaceLayoutState,
    controller?: ReturnType<typeof createWorkspaceController>
): void {
    setContext(CONTEXT_KEY, { getState, controller });
}

export function usePointCloudWorkspaceLayoutContext(): () => PointCloudWorkspaceLayoutState {
    const context = getContext<WorkspaceContext | undefined>(CONTEXT_KEY);
    if (!context) throw new Error('Point cloud workspace layout context is missing.');
    return context.getState;
}

/** Reads the workspace shell's controllers without forwarding them through layout components. */
export function useWorkspaceControllerContext(): ReturnType<typeof createWorkspaceController> {
    const context = getContext<WorkspaceContext | undefined>(CONTEXT_KEY);
    if (!context?.controller)
        throw new Error('Point cloud workspace controller context is missing.');
    return context.controller;
}
