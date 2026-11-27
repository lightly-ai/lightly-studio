<script lang="ts">
    import { Toaster } from 'svelte-sonner';
    import type { WorkspaceOptions } from './workspaceOptions';
    import { createWorkspaceController } from './createWorkspaceController.svelte';
    import { providePointCloudWorkspaceLayoutContext } from './pointCloudWorkspaceLayoutContext.svelte';
    import { providePortalTarget } from '$lib/contexts/PortalTarget';
    import { cn } from '$lib/utils';
    import WorkspaceChrome from './WorkspaceChrome/WorkspaceChrome.svelte';
    import WorkspaceFullscreenBar from './WorkspaceFullscreenBar/WorkspaceFullscreenBar.svelte';
    import WorkspacePanels from './WorkspacePanels/WorkspacePanels.svelte';
    import WorkspaceClassDialog from './WorkspaceClassDialog/WorkspaceClassDialog.svelte';

    let options: WorkspaceOptions = $props();
    const controller = createWorkspaceController(() => options);
    providePointCloudWorkspaceLayoutContext(controller.getLayout, controller);
    providePortalTarget(() => controller.fullscreen.portalTarget);
    const isFullscreen = $derived(controller.fullscreen.isFullscreen);
</script>

<svelte:window onkeydown={controller.playback.handleWindowKeydown} />
<!-- In fullscreen, the workspace takes the page background and card layout of the app. -->
<div
    bind:this={controller.fullscreen.containerEl}
    class={cn(
        'flex h-full min-h-0 w-full min-w-0 flex-col',
        isFullscreen && 'bg-background text-foreground dark:bg-black'
    )}
    data-testid="point-cloud-labeling-workspace"
>
    {#if isFullscreen}
        <WorkspaceFullscreenBar />
    {/if}
    <div
        class={cn(
            'flex min-h-0 min-w-0 flex-1 flex-col',
            isFullscreen && 'mx-4 mb-4 rounded-panel bg-card px-4 py-2'
        )}
    >
        <WorkspaceChrome />
        <WorkspacePanels />
    </div>
    <WorkspaceClassDialog />
    <!-- The app toaster is outside the fullscreen element, so the browser does not show it. -->
    {#if isFullscreen}
        <Toaster richColors />
    {/if}
</div>
