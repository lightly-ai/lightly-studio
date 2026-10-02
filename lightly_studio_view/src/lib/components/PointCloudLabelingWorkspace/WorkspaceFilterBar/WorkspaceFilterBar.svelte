<script lang="ts">
    import WorkspaceChannelSelect from './WorkspaceChannelSelect/WorkspaceChannelSelect.svelte';
    import { Select } from '$lib/components/Select';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Slider } from '$lib/components/ui/slider';
    import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';

    interface Props {
        /** Coordinate frames the scene can be shown in. */
        referenceFrames: readonly { readonly id: string; readonly name: string }[];

        /** ID of the coordinate frame the scene is shown in. */
        referenceFrameId: string;

        /** Shows the scene in another coordinate frame by its ID. */
        onSelectReferenceFrame: (frameId: string) => void;

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

        /** Whether new point clouds are added to the scene instead of replacing it. */
        accumulatePointClouds: boolean;

        /** Turns point-cloud accumulation on or off. */
        onAccumulatePointCloudsChange: (accumulate: boolean) => void;

        /** Screen-space size of the points in the scene, in pixels. */
        pointSize: number;

        /** Sets the size of the points in the scene. */
        onPointSizeChange: (pointSize: number) => void;
    }

    let {
        referenceFrames,
        referenceFrameId,
        onSelectReferenceFrame,
        lidarChannels,
        cameraChannels,
        selectedLidarChannels,
        selectedCameraChannels,
        onToggleLidarChannel,
        onToggleCameraChannel,
        accumulatePointClouds,
        onAccumulatePointCloudsChange,
        pointSize,
        onPointSizeChange
    }: Props = $props();

    const frameItems = $derived(
        referenceFrames.map((frame) => ({
            value: frame.id,
            label: frame.name,
            testId: `workspace-frame-select-${frame.id}`
        }))
    );
    const frameTriggerLabel = $derived(
        `Frame: ${referenceFrames.find((frame) => frame.id === referenceFrameId)?.name ?? referenceFrameId}`
    );
</script>

<div class="flex shrink-0 items-center gap-4" data-testid="workspace-filter-bar">
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
    <label class="flex items-center gap-2 text-sm">
        <Checkbox
            checked={accumulatePointClouds}
            onCheckedChange={onAccumulatePointCloudsChange}
            data-testid="workspace-accumulate-checkbox"
        />
        Accumulate point clouds
    </label>
    <div class="flex items-center gap-2 text-sm">
        <span id="workspace-point-size-label">Point size</span>
        <Slider
            type="single"
            value={pointSize}
            onValueChange={onPointSizeChange}
            min={1}
            max={10}
            step={0.5}
            class="w-32"
            aria-labelledby="workspace-point-size-label"
            data-testid="workspace-point-size-slider"
        />
        <span class="w-8 tabular-nums text-muted-foreground">{pointSize}px</span>
    </div>
</div>
