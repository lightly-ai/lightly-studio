<script lang="ts">
    import { Pane, PaneGroup, PaneResizer } from 'paneforge';
    import PointCloudWorkspaceMainColumn from '../PointCloudWorkspaceMainColumn.svelte';
    import PointCloudRightSidePanel from '../PointCloudRightSidePanel';
    import WorkspaceStatusPanel from '../WorkspaceStatusPanel/WorkspaceStatusPanel.svelte';
    import { useWorkspaceControllerContext } from '../pointCloudWorkspaceLayoutContext.svelte';
    import { useSidePanel } from '../useSidePanel/useSidePanel.svelte';
    import { hasMinimumRole, useAuth } from '$lib/hooks';
    const controller = useWorkspaceControllerContext();
    const { workspace, editing, data, presentation, targetSource } = controller;
    const sidePanel = useSidePanel(() => editing.selectedCuboidId);
    const { user } = useAuth();
    // The source for new cuboids is picked in edit mode only, like the other editing controls.
    const canPickSource = $derived(
        hasMinimumRole(user?.role, 'labeler') && presentation.isEditingMode
    );
</script>

<div class="flex min-h-0 flex-1">
    {#if workspace.status === 'unsupported' || workspace.status === 'error'}
        <WorkspaceStatusPanel
            status={workspace.status}
            onRetry={controller.options.onRetry ?? workspace.retry}
        />
    {:else}
        <PaneGroup direction="horizontal" class="min-h-0 flex-1">
            <Pane defaultSize={78} minSize={50} class="flex min-h-0 flex-col">
                <PointCloudWorkspaceMainColumn />
            </Pane>
            <PaneResizer
                class="group relative flex w-2 cursor-col-resize items-center justify-center bg-card transition-colors hover:bg-card"
            >
                <div
                    class="flex flex-col gap-0.5 opacity-40 transition-opacity group-hover:opacity-100"
                >
                    <span class="size-1 rounded-full bg-muted-foreground"></span>
                    <span class="size-1 rounded-full bg-muted-foreground"></span>
                    <span class="size-1 rounded-full bg-muted-foreground"></span>
                </div>
            </PaneResizer>
            <Pane
                bind:this={sidePanel.pane}
                defaultSize={22}
                minSize={16}
                maxSize={40}
                collapsedSize={0}
                collapsible
                onCollapse={() => sidePanel.setCollapsed(true)}
                onExpand={() => sidePanel.setCollapsed(false)}
            >
                <PointCloudRightSidePanel
                    cuboids={editing.annotations}
                    annotationClasses={data.annotationClasses}
                    annotationSources={data.annotationSources}
                    bind:selectedCuboidId={editing.selectedCuboidId}
                    sequence={workspace.sequenceSample}
                    onSequenceTagsChange={workspace.refetchSequenceSample}
                    tick={data.tick}
                    onTagsChange={() => void workspace.tickDetails.refetch()}
                    onCuboidTagsChange={() => void workspace.tickDetails.refetch()}
                    editable={presentation.isEditingMode}
                    onCuboidTransform={editing.panelCuboidTransform}
                    onLabelChange={editing.handleLabelChange}
                    onTrackChange={editing.handleTrackChange}
                    onDeleteCuboid={presentation.isEditingMode
                        ? editing.handleDeleteCuboid
                        : undefined}
                    targetSourceName={targetSource.targetSource}
                    pendingSourceName={targetSource.typedSource}
                    needsPick={targetSource.needsPick}
                    onPickSource={canPickSource ? targetSource.setTarget : undefined}
                    isCuboidHidden={controller.visibility.isCuboidHidden}
                    isSourceHidden={controller.visibility.isSourceHidden}
                    onToggleTrackVisibility={controller.visibility.toggleTrack}
                    onToggleSourceVisibility={controller.visibility.toggleSource}
                />
            </Pane>
        </PaneGroup>
    {/if}
</div>
