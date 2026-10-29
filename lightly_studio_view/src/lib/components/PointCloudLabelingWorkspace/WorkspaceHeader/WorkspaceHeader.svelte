<script lang="ts">
    import { ChevronDown, ChevronUp, Maximize2, Minimize2 } from '@lucide/svelte';
    import WorkspaceBreadcrumb from './WorkspaceBreadcrumb.svelte';
    import { Button } from '$lib/components';
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
        /** Whether the camera strip is reduced to its header. */
        cameraStripCollapsed?: boolean;
        /** Expands or collapses the camera strip. */
        onToggleCameraStrip?: () => void;
    }

    let {
        sequenceId,
        sourcePath = [],
        isFullscreen,
        onToggleFullscreen,
        cameraStripCollapsed = false,
        onToggleCameraStrip
    }: Props = $props();
</script>

<header
    class="flex shrink-0 items-center justify-between border-b pb-2"
    data-testid="workspace-header"
>
    <WorkspaceBreadcrumb {sequenceId} {sourcePath} />
    <div class="flex shrink-0 items-center gap-1">
        {#if onToggleCameraStrip}
            <Button
                variant="ghost"
                icon={cameraStripCollapsed ? ChevronUp : ChevronDown}
                ariaLabel={cameraStripCollapsed ? 'Show camera strip' : 'Hide camera strip'}
                buttonProps={{
                    type: 'button',
                    size: 'sm',
                    class: 'h-8 w-8 p-0',
                    onclick: onToggleCameraStrip
                }}
            />
        {/if}
        <Button
            variant="ghost"
            icon={isFullscreen ? Minimize2 : Maximize2}
            ariaLabel={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            buttonProps={{ onclick: onToggleFullscreen, size: 'sm', class: 'h-8 w-8 p-0' }}
        />
    </div>
</header>
