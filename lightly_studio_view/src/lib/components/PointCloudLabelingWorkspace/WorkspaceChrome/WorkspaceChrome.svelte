<script lang="ts">
    import Camera from '@lucide/svelte/icons/camera';
    import Grid2x2 from '@lucide/svelte/icons/grid-2x2';
    import PanelRight from '@lucide/svelte/icons/panel-right';
    import WorkspaceHeader from '../WorkspaceHeader/WorkspaceHeader.svelte';
    import WorkspaceFilterBar from '../WorkspaceFilterBar/WorkspaceFilterBar.svelte';
    import { useWorkspaceControllerContext } from '../pointCloudWorkspaceLayoutContext.svelte';
    const controller = useWorkspaceControllerContext();
    const {
        workspace,
        presentation,
        fullscreen,
        cameraPane,
        detailsPane,
        lidarSelection,
        cameraSelection
    } = controller;

    const layoutToggles = $derived([
        {
            id: 'orthographic',
            label: 'Orthographic views',
            icon: Grid2x2,
            isActive: presentation.showOrthographicViews
        },
        {
            id: 'camera',
            label: 'Camera projections',
            icon: Camera,
            isActive: !cameraPane.collapsed
        },
        { id: 'details', label: 'Details', icon: PanelRight, isActive: !detailsPane.collapsed }
    ]);
    const toggleLayout = (id: string) => {
        if (id === 'orthographic') {
            presentation.toggleOrthographicProjections(!presentation.showOrthographicViews);
        } else if (id === 'camera') {
            cameraPane.toggle();
        } else if (id === 'details') {
            detailsPane.toggle();
        }
    };
</script>

<WorkspaceHeader
    sequenceId={controller.options.sequenceId}
    sourcePath={controller.options.sourcePath}
    isFullscreen={fullscreen.isFullscreen}
    onToggleFullscreen={fullscreen.toggleFullscreen}
    {layoutToggles}
    onToggleLayout={toggleLayout}
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
