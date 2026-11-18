<script lang="ts">
    import { SidePanelToggleButton } from '$lib/components';
    import WorkflowFileStatus from '$lib/components/Workflow/WorkflowFileStatus/WorkflowFileStatus.svelte';
    import WorkflowFileActions from '$lib/components/Workflow/WorkflowFileActions/WorkflowFileActions.svelte';
    import WorkflowReadOnlyBanner from '$lib/components/Workflow/WorkflowReadOnlyBanner/WorkflowReadOnlyBanner.svelte';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { useWorkflowFileContext } from '$lib/contexts/WorkflowFile.svelte';
    import BreadcrumbHeaderActions from '$lib/components/SampleDetails/BreadcrumbHeaderActions/BreadcrumbHeaderActions.svelte';
    import type { Snippet } from 'svelte';

    /** Inputs for the top row of a sample details page. */
    interface Props {
        /** Collection whose samples the edit and plugin actions apply to. */
        collectionId: string;
        /** Path to the sample, shown on the left. */
        breadcrumb: Snippet;
        /** Page-specific buttons, shown after the edit actions. */
        extraActions?: Snippet;
        /** Shows the button that collapses the page's side panel. */
        showSidePanelToggle?: boolean;
    }

    const { collectionId, breadcrumb, extraActions, showSidePanelToggle = true }: Props = $props();

    const workflow = useWorkflowFileContext();
</script>

<div class="flex w-full items-center justify-between">
    <div class="flex items-center gap-4">
        {@render breadcrumb()}
        {#if workflow?.file}
            <WorkflowFileStatus file={workflow.file} />
        {/if}
    </div>
    <div class="flex items-center gap-1">
        {#if workflow?.file}
            <WorkflowFileActions
                file={workflow.file}
                transitioning={workflow.transitioning}
                onTransition={workflow.transition}
            />
        {/if}
        <BreadcrumbHeaderActions {collectionId} />
        {@render extraActions?.()}
        {#if showSidePanelToggle}
            <SidePanelToggleButton />
        {/if}
    </div>
</div>
<Separator class="bg-border-hard" />
{#if workflow?.file}
    <WorkflowReadOnlyBanner file={workflow.file} />
{:else if workflow?.isError}
    <p role="alert" class="text-sm text-destructive">
        Could not load the batch for this file. It stays read-only.
    </p>
{/if}
