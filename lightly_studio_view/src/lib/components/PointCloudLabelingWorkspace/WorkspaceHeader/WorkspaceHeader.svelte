<script lang="ts">
    import { ChevronDown, ChevronUp, Maximize2, Minimize2 } from '@lucide/svelte';
    import WorkspaceBreadcrumb from './WorkspaceBreadcrumb.svelte';
    import { Button } from '$lib/components';
    import DetailsHeader from '$lib/components/DetailsHeader/DetailsHeader.svelte';
    import type { WorkspaceCrumb } from '../types';

    /** Inputs and callbacks for workspace header. */
    interface Props {
        /**
         * Collection the edit, plugin and settings actions apply to. Without it the header
         * shows only the breadcrumb, camera strip and fullscreen buttons.
         */
        collectionId?: string;
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
        collectionId,
        sequenceId,
        sourcePath = [],
        isFullscreen,
        onToggleFullscreen,
        cameraStripCollapsed = false,
        onToggleCameraStrip
    }: Props = $props();

    // Fullscreen keeps the view uncluttered; the edit shortcuts still work.
    const compact = $derived(isFullscreen || !collectionId);
</script>

<header
    class={['flex shrink-0 flex-col gap-2 pb-2', compact && 'border-b']}
    data-testid="workspace-header"
>
    <DetailsHeader collectionId={collectionId ?? ''} {compact} showSidePanelToggle={false}>
        {#snippet breadcrumb()}
            <WorkspaceBreadcrumb {sequenceId} {sourcePath} />
        {/snippet}
        {#snippet extraActions()}
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
        {/snippet}
    </DetailsHeader>
</header>
