<script lang="ts">
    import { Pane, PaneGroup, PaneResizer } from 'paneforge';
    import PointCloudWorkspaceMainColumn from '../PointCloudWorkspaceMainColumn.svelte';
    import PointCloudRightSidePanel from '../PointCloudRightSidePanel';
    import { WorkspacePanel } from '../WorkspacePanel';
    import WorkspaceStatusPanel from '../WorkspaceStatusPanel/WorkspaceStatusPanel.svelte';
    import { useWorkspaceControllerContext } from '../pointCloudWorkspaceLayoutContext.svelte';
    import { hasMinimumRole, useAuth } from '$lib/hooks';
    import { useQueryClient } from '@tanstack/svelte-query';
    import { TICK_TAGS_QUERY_KEY } from '../FrameTimeline/tickTagsQueryKey';
    const controller = useWorkspaceControllerContext();
    const { workspace, editing, data, presentation, targetSource, detailsPane } = controller;
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const refetchTickTags = () => {
        void workspace.tickDetails.refetch();
        void queryClient.invalidateQueries({ queryKey: TICK_TAGS_QUERY_KEY });
    };
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
            <Pane defaultSize={72} minSize={50} class="flex min-h-0 flex-col">
                <PointCloudWorkspaceMainColumn />
            </Pane>
            <PaneResizer
                class="group relative flex w-2 cursor-col-resize items-center justify-center bg-card transition-colors hover:bg-card {detailsPane.collapsed
                    ? 'hidden'
                    : ''}"
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
                bind:this={detailsPane.pane}
                defaultSize={28}
                minSize={20}
                maxSize={45}
                collapsedSize={0}
                collapsible
                onCollapse={() => detailsPane.setCollapsed(true)}
                onExpand={() => detailsPane.setCollapsed(false)}
            >
                {#if !detailsPane.collapsed}
                    <WorkspacePanel
                        title="Details"
                        onHide={detailsPane.toggle}
                        class="h-full border-l"
                        testId="workspace-details-panel"
                    >
                        <PointCloudRightSidePanel
                            cuboids={editing.annotations}
                            annotationClasses={data.annotationClasses}
                            annotationSources={data.annotationSources}
                            bind:selectedCuboidId={editing.selectedCuboidId}
                            sequence={workspace.sequenceSample}
                            onSequenceTagsChange={workspace.refetchSequenceSample}
                            tick={data.tick}
                            onTagsChange={refetchTickTags}
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
                    </WorkspacePanel>
                {/if}
            </Pane>
        </PaneGroup>
    {/if}
</div>
