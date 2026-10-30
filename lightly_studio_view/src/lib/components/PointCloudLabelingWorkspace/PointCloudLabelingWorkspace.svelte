<script lang="ts">
    import type { WorkspaceOptions } from './workspaceOptions';
    import { createWorkspaceController } from './createWorkspaceController.svelte';
    import { providePointCloudWorkspaceLayoutContext } from './pointCloudWorkspaceLayoutContext.svelte';
    import WorkspaceChrome from './WorkspaceChrome/WorkspaceChrome.svelte';
    import WorkspacePanels from './WorkspacePanels/WorkspacePanels.svelte';
    import WorkspaceClassDialog from './WorkspaceClassDialog/WorkspaceClassDialog.svelte';

    // This workspace is not compiled as a custom element; keep its inputs reactive as a group.
    // svelte-ignore custom_element_props_identifier
    let options: WorkspaceOptions = $props();
    const controller = createWorkspaceController(() => options);
    providePointCloudWorkspaceLayoutContext(controller.getLayout, controller);
</script>

<svelte:window onkeydown={controller.playback.handleWindowKeydown} />
<div
    bind:this={controller.fullscreen.containerEl}
    class="flex h-full min-h-0 w-full min-w-0 flex-col"
    data-testid="point-cloud-labeling-workspace"
>
    <WorkspaceChrome />
    <WorkspacePanels />
</div>
<WorkspaceClassDialog />
