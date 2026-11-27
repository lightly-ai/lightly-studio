<script lang="ts">
    import Maximize2 from '@lucide/svelte/icons/maximize-2';
    import Minimize2 from '@lucide/svelte/icons/minimize-2';
    import WorkspaceBreadcrumb from './WorkspaceBreadcrumb.svelte';
    import { Button } from '$lib/components';
    import { WorkspaceLayoutToggles, type LayoutToggle } from '../WorkspaceLayoutToggles';
    import type { WorkspaceCrumb } from '../types';

    /** Inputs and callbacks for workspace header. */
    interface Props {
        /** Sequence displayed by the labeling workspace. */
        sequenceId: string;
        /** Dataset -> collection -> sample path of the point cloud being labeled. */
        sourcePath?: readonly WorkspaceCrumb[];
        /** Whether the workspace container is in browser fullscreen mode. */
        isFullscreen: boolean;
        /** Enters or leaves browser fullscreen mode. */
        onToggleFullscreen: () => void;
        /** Icon toggles that show or hide the workspace panels. */
        layoutToggles?: readonly LayoutToggle[];
        /** Shows or hides the panel with the given toggle id. */
        onToggleLayout?: (id: string) => void;
    }

    let {
        sequenceId,
        sourcePath = [],
        isFullscreen,
        onToggleFullscreen,
        layoutToggles = [],
        onToggleLayout = () => {}
    }: Props = $props();
</script>

<header
    class="flex shrink-0 items-center justify-between border-b pb-2"
    data-testid="workspace-header"
>
    <WorkspaceBreadcrumb {sequenceId} {sourcePath} />
    <div class="flex shrink-0 items-center gap-1">
        {#if layoutToggles.length > 0}
            <WorkspaceLayoutToggles toggles={layoutToggles} onToggle={onToggleLayout} />
            <div class="mx-1 h-5 w-px bg-border"></div>
        {/if}
        <Button
            variant="ghost"
            icon={isFullscreen ? Minimize2 : Maximize2}
            ariaLabel={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            buttonProps={{ onclick: onToggleFullscreen, size: 'sm', class: 'h-8 w-8 p-0' }}
        />
    </div>
</header>
