<script lang="ts">
    import WorkspaceChannelFilters from './WorkspaceChannelFilters/WorkspaceChannelFilters.svelte';
    import WorkspaceViewFilters from './WorkspaceViewFilters/WorkspaceViewFilters.svelte';
    import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';
    import type { ColorMode } from '$lib/components/PointCloudViewer';

    interface Props {
        /** Coordinate frames the scene can be shown in. */
        referenceFrames: readonly { readonly name: string }[];

        /** ID of the coordinate frame the point clouds are shown in. */
        referenceFrameId: string;

        /** Shows the point clouds in another coordinate frame by its ID. */
        onSelectReferenceFrame: (frameId: string) => void;

        /** Whether the active tick is shown in the sensor frames instead. */
        isShowingSensorFrames?: boolean;

        /** Point-cloud channels rendered as timeline lanes. */
        lidarChannels: ChannelSummaryView[];

        /** Image and video channels rendered as timeline lanes. */
        cameraChannels: ChannelSummaryView[];

        /** `channel_id`s of the lidar channels currently shown. */
        selectedLidarChannels: number[];

        /** `channel_id`s of the camera channels currently shown. */
        selectedCameraChannels: number[];

        colorMode: Exclude<ColorMode, 'none'>;
        onColorModeChange: (colorMode: Exclude<ColorMode, 'none'>) => void;

        /** Toggles a lidar channel on or off by its `channel_id`. */
        onToggleLidarChannel: (channelId: number) => void;

        /** Toggles a camera channel on or off by its `channel_id`. */
        onToggleCameraChannel: (channelId: number) => void;

        /** Replaces the selected LiDAR channels. */
        onSetLidarChannels: (channelIds: number[]) => void;

        /** Replaces the selected camera channels. */
        onSetCameraChannels: (channelIds: number[]) => void;
    }

    let {
        referenceFrames,
        referenceFrameId,
        onSelectReferenceFrame,
        isShowingSensorFrames = false,
        lidarChannels,
        cameraChannels,
        selectedLidarChannels,
        selectedCameraChannels,
        colorMode,
        onColorModeChange,
        onToggleLidarChannel,
        onToggleCameraChannel,
        onSetLidarChannels,
        onSetCameraChannels
    }: Props = $props();
</script>

<div class="flex shrink-0 items-center gap-4 border-b py-2" data-testid="workspace-filter-bar">
    <WorkspaceViewFilters
        {referenceFrames}
        {referenceFrameId}
        {onSelectReferenceFrame}
        {isShowingSensorFrames}
        {colorMode}
        {onColorModeChange}
    />
    <WorkspaceChannelFilters
        {lidarChannels}
        {cameraChannels}
        {selectedLidarChannels}
        {selectedCameraChannels}
        {onToggleLidarChannel}
        {onToggleCameraChannel}
        {onSetLidarChannels}
        {onSetCameraChannels}
    />
</div>
