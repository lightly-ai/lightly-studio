<script lang="ts">
    import WorkspaceChannelSelect from './WorkspaceChannelSelect/WorkspaceChannelSelect.svelte';
    import { Select } from '$lib/components/Select';
    import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';

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

        /** Toggles a lidar channel on or off by its `channel_id`. */
        onToggleLidarChannel: (channelId: number) => void;

        /** Toggles a camera channel on or off by its `channel_id`. */
        onToggleCameraChannel: (channelId: number) => void;
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
        onToggleLidarChannel,
        onToggleCameraChannel
    }: Props = $props();

    const frameItems = $derived(
        referenceFrames.map((frame) => ({
            value: frame.name,
            label: frame.name,
            testId: `workspace-frame-select-${frame.name}`
        }))
    );
    const frameTriggerLabel = $derived(`Frame: ${referenceFrameId}`);
</script>

<div class="flex shrink-0 items-center gap-4 border-b py-2" data-testid="workspace-filter-bar">
    {#if referenceFrames.length > 0}
        <Select
            items={frameItems}
            value={referenceFrameId}
            triggerLabel={frameTriggerLabel}
            size="xs"
            class="w-40"
            testId="workspace-frame-select"
            onValueChange={onSelectReferenceFrame}
        />
        {#if isShowingSensorFrames}
            <span class="text-xs text-muted-foreground" data-testid="workspace-frame-fallback">
                No transform at this tick. Showing sensor frames.
            </span>
        {/if}
    {/if}
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
