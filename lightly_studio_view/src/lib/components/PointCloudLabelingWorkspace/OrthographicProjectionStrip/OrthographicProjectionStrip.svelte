<script lang="ts">
    import WorkspaceViewport from '../WorkspaceViewport/WorkspaceViewport.svelte';
    import { useWorkspaceSceneLayout } from '../workspaceSceneLayoutContext.svelte';
    import { cn } from '$lib/utils';
    const scene = useWorkspaceSceneLayout();
    const views = ['top', 'side', 'front'] as const;
</script>

<div
    class={cn(
        'grid h-full min-h-0 bg-card',
        scene.expandedProjection ? 'grid-cols-1' : 'grid-cols-3 gap-2 border-t-8 border-card'
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
