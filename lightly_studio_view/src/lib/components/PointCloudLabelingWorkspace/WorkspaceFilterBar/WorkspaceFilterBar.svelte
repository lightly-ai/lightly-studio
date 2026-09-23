<script lang="ts">
    import WorkspaceChannelSelect from './WorkspaceChannelSelect/WorkspaceChannelSelect.svelte';
    import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';

    interface Props {
        /** Point-cloud channels rendered as timeline lanes. */
        lidarChannels: ChannelSummaryView[];

        /** Image and video channels rendered as timeline lanes. */
        cameraChannels: ChannelSummaryView[];

        /** `channel_id`s of the lidar channels currently shown. */
        selectedLidarChannels: number[];

        /** `channel_id`s of the camera channels currently shown. */
        selectedCameraChannels: number[];

        /** Toggles a lidar channel on or off by its `channel_id`. */
        onToggleLidarChannel: (channelId: number) => void;

        /** Toggles a camera channel on or off by its `channel_id`. */
        onToggleCameraChannel: (channelId: number) => void;
    }

    let {
        lidarChannels,
        cameraChannels,
        selectedLidarChannels,
        selectedCameraChannels,
        onToggleLidarChannel,
        onToggleCameraChannel
    }: Props = $props();
</script>

<div
    class="flex shrink-0 items-center gap-4 border-b bg-background px-4 py-2"
    data-testid="workspace-filter-bar"
>
    <WorkspaceChannelSelect
        label="Lidar"
        channels={lidarChannels}
        selectedChannels={selectedLidarChannels}
        onToggleChannel={onToggleLidarChannel}
        testId="workspace-lidar-select"
    />
    <WorkspaceChannelSelect
        label="Camera"
        channels={cameraChannels}
        selectedChannels={selectedCameraChannels}
        onToggleChannel={onToggleCameraChannel}
        testId="workspace-camera-select"
    />
</div>
