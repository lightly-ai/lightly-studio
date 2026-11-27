<script lang="ts">
    import Maximize2 from '@lucide/svelte/icons/maximize-2';
    import Minimize2 from '@lucide/svelte/icons/minimize-2';
    import WorkspaceBreadcrumb from './WorkspaceBreadcrumb.svelte';
    import { Button } from '$lib/components';
    import DetailsHeader from '$lib/components/DetailsHeader/DetailsHeader.svelte';
    import { WorkspaceLayoutToggles, type LayoutToggle } from '../WorkspaceLayoutToggles';
    import type { WorkspaceCrumb } from '../types';

    /** Inputs and callbacks for workspace header. */
    interface Props {
        /**
         * Collection the edit, plugin and settings actions apply to. Without it the header
         * shows only the breadcrumb, layout toggles and fullscreen button.
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
        /** Icon toggles that show or hide the workspace panels. */
        layoutToggles?: readonly LayoutToggle[];
        /** Shows or hides the panel with the given toggle id. */
        onToggleLayout?: (id: string) => void;
    }

    let {
        collectionId,
        sequenceId,
        sourcePath = [],
        isFullscreen,
        onToggleFullscreen,
        layoutToggles = [],
        onToggleLayout = () => {}
    }: Props = $props();

    // Fullscreen keeps the view uncluttered; the edit shortcuts still work.
    const compact = $derived(isFullscreen || !collectionId);
</script>

<header
    class={['flex shrink-0 flex-col gap-2 pb-2', compact && 'border-b']}
    data-testid="workspace-header"
>
    <!-- The layout toggles include the details panel, so the generic side-panel toggle is off. -->
    <DetailsHeader collectionId={collectionId ?? ''} {compact} showSidePanelToggle={false}>
        {#snippet breadcrumb()}
            <WorkspaceBreadcrumb {sequenceId} {sourcePath} />
        {/snippet}
        {#snippet extraActions()}
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
        {/snippet}
    </DetailsHeader>
</header>
