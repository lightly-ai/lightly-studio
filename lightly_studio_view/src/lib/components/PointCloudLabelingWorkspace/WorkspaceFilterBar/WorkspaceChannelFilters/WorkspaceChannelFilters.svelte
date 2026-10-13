<script lang="ts">
    import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';
    import WorkspaceChannelSelect from '../WorkspaceChannelSelect/WorkspaceChannelSelect.svelte';

    interface Props {
        lidarChannels: ChannelSummaryView[];
        cameraChannels: ChannelSummaryView[];
        selectedLidarChannels: number[];
        selectedCameraChannels: number[];
        onToggleLidarChannel: (channelId: number) => void;
        onToggleCameraChannel: (channelId: number) => void;
        onSetLidarChannels: (channelIds: number[]) => void;
        onSetCameraChannels: (channelIds: number[]) => void;
    }

    let {
        lidarChannels,
        cameraChannels,
        selectedLidarChannels,
        selectedCameraChannels,
        onToggleLidarChannel,
        onToggleCameraChannel,
        onSetLidarChannels,
        onSetCameraChannels
    }: Props = $props();
</script>

<WorkspaceChannelSelect
    label="Lidar"
    channels={lidarChannels}
    selectedChannels={selectedLidarChannels}
    onToggleChannel={onToggleLidarChannel}
    onSetChannels={onSetLidarChannels}
    testId="workspace-lidar-select"
/>
<WorkspaceChannelSelect
    label="Camera"
    channels={cameraChannels}
    selectedChannels={selectedCameraChannels}
    onToggleChannel={onToggleCameraChannel}
    onSetChannels={onSetCameraChannels}
    testId="workspace-camera-select"
/>
