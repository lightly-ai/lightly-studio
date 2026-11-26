<script lang="ts">
    import WorkspaceViewFilters from './WorkspaceViewFilters/WorkspaceViewFilters.svelte';
    import { WorkspaceChannelSelect } from '../WorkspaceChannelSelect';
    import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';
    import type { ColorMode } from '$lib/components/PointCloudViewer';

    /** What the 3D scene shows: the coordinate frame, the point color and the lidar channels. */
    interface Props {
        /** Coordinate frames the scene can be shown in. */
        referenceFrames: readonly { readonly name: string }[];
        /** ID of the coordinate frame the point clouds are shown in. */
        referenceFrameId: string;
        /** Shows the point clouds in another coordinate frame by its ID. */
        onSelectReferenceFrame: (frameId: string) => void;
        /** Whether the active tick is shown in the sensor frames instead. */
        isShowingSensorFrames?: boolean;
        colorMode: Exclude<ColorMode, 'none'>;
        onColorModeChange: (colorMode: Exclude<ColorMode, 'none'>) => void;
        /** Point-cloud channels of the sequence. */
        lidarChannels: ChannelSummaryView[];
        /** `channel_id`s of the lidar channels currently shown. */
        selectedLidarChannels: number[];
        /** Toggles a lidar channel on or off by its `channel_id`. */
        onToggleLidarChannel: (channelId: number) => void;
        /** Replaces the selected lidar channels. */
        onSetLidarChannels: (channelIds: number[]) => void;
    }

    let {
        referenceFrames,
        referenceFrameId,
        onSelectReferenceFrame,
        isShowingSensorFrames = false,
        colorMode,
        onColorModeChange,
        lidarChannels,
        selectedLidarChannels,
        onToggleLidarChannel,
        onSetLidarChannels
    }: Props = $props();
</script>

<div class="flex flex-col gap-2" data-testid="workspace-scene-filters">
    <WorkspaceViewFilters
        {referenceFrames}
        {referenceFrameId}
        {onSelectReferenceFrame}
        {isShowingSensorFrames}
        {colorMode}
        {onColorModeChange}
    />
    <WorkspaceChannelSelect
        label="Lidar"
        channels={lidarChannels}
        selectedChannels={selectedLidarChannels}
        onToggleChannel={onToggleLidarChannel}
        onSetChannels={onSetLidarChannels}
        testId="workspace-lidar-select"
    />
</div>
