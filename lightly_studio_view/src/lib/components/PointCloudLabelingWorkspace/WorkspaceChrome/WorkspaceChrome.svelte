<script lang="ts">
    import WorkspaceHeader from '../WorkspaceHeader/WorkspaceHeader.svelte';
    import WorkspaceFilterBar from '../WorkspaceFilterBar/WorkspaceFilterBar.svelte';
    import { useWorkspaceControllerContext } from '../pointCloudWorkspaceLayoutContext.svelte';
    const controller = useWorkspaceControllerContext();
    const { workspace, presentation, fullscreen, cameraPane, lidarSelection, cameraSelection } =
        controller;
</script>

<WorkspaceHeader
    sequenceId={controller.options.sequenceId}
    sourcePath={controller.options.sourcePath}
    isFullscreen={fullscreen.isFullscreen}
    onToggleFullscreen={fullscreen.toggleFullscreen}
    cameraStripCollapsed={cameraPane.collapsed}
    onToggleCameraStrip={cameraPane.toggle}
/>
<WorkspaceFilterBar
    referenceFrames={workspace.referenceFrames}
    referenceFrameId={workspace.referenceFrameId}
    onSelectReferenceFrame={workspace.selectReferenceFrame}
    isShowingSensorFrames={workspace.isShowingSensorFrames}
    lidarChannels={workspace.lidarChannels}
    cameraChannels={workspace.cameraChannels}
    selectedLidarChannels={lidarSelection.selectedChannelIds}
    selectedCameraChannels={cameraSelection.selectedChannelIds}
    colorMode={presentation.colorMode}
    onColorModeChange={presentation.setColorMode}
    onToggleLidarChannel={lidarSelection.toggleChannel}
    onToggleCameraChannel={cameraSelection.toggleChannel}
    onSetLidarChannels={lidarSelection.setChannels}
    onSetCameraChannels={cameraSelection.setChannels}
/>
