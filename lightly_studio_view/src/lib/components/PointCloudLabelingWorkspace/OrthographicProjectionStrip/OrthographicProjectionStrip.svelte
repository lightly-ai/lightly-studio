<script lang="ts">
    import ChevronDown from '@lucide/svelte/icons/chevron-down';
    import ChevronUp from '@lucide/svelte/icons/chevron-up';
    import { Button } from '$lib/components';
    import WorkspaceViewport from '../WorkspaceViewport/WorkspaceViewport.svelte';
    import WorkspacePanelHeader from '../WorkspacePanelHeader/WorkspacePanelHeader.svelte';
    import { useWorkspaceSceneLayout } from '../workspaceSceneLayoutContext.svelte';
    import { cn } from '$lib/utils';

    interface Props {
        /** When true, only the header shows and the views are not rendered. */
        collapsed: boolean;
        /** Collapses or expands the strip. */
        onToggleCollapsed: () => void;
    }

    let { collapsed, onToggleCollapsed }: Props = $props();
    const scene = useWorkspaceSceneLayout();
    const views = ['top', 'side', 'front'] as const;
</script>

<div class="flex h-full min-h-0 flex-col bg-card" data-testid="orthographic-projection-strip">
    {#if !scene.expandedProjection}
        <div class="border-t-8 border-card">
            <WorkspacePanelHeader title="Orthographic projections">
                {#snippet actions()}
                    <Button
                        variant="ghost"
                        icon={collapsed ? ChevronUp : ChevronDown}
                        ariaLabel={collapsed
                            ? 'Expand orthographic projections'
                            : 'Collapse orthographic projections'}
                        buttonProps={{
                            type: 'button',
                            size: 'xs',
                            class: 'h-7 w-7 p-0',
                            onclick: onToggleCollapsed
                        }}
                    />
                {/snippet}
            </WorkspacePanelHeader>
        </div>
    {/if}
    {#if !collapsed}
        <div
            class={cn(
                'grid min-h-0 flex-1',
                scene.expandedProjection ? 'grid-cols-1' : 'grid-cols-3 gap-2'
            )}
        >
            {#each views as mode (mode)}
                <div
                    class="relative min-h-0 min-w-0 overflow-hidden"
                    hidden={scene.expandedProjection !== null && scene.expandedProjection !== mode}
                    data-testid={`projection-${mode}`}
                >
                    <WorkspaceViewport cameraMode={mode} />
                </div>
            {/each}
        </div>
    {/if}
</div>
