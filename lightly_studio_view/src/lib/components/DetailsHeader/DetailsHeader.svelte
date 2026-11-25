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
        /**
         * Shows only the breadcrumb and extra actions, e.g. in fullscreen. The edit actions
         * stay mounted (hidden) so their keyboard shortcuts keep working.
         */
        compact?: boolean;
    }

    const {
        collectionId,
        breadcrumb,
        extraActions,
        showSidePanelToggle = true,
        compact = false
    }: Props = $props();

    const context = useWorkflowFileContext();
    const workflow = $derived(compact ? undefined : context);
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
                fileState={workflow.file.state}
                allowedTransitions={workflow.file.allowed_transitions}
                yourRole={workflow.file.your_role}
                transitioning={workflow.transitioning}
                onTransition={workflow.transition}
                onAdvance={workflow.goToNext}
            />
        {/if}
        <div class={compact ? 'hidden' : 'contents'} hidden={compact}>
            <BreadcrumbHeaderActions {collectionId} />
        </div>
        {@render extraActions?.()}
        {#if showSidePanelToggle && !compact}
            <SidePanelToggleButton />
        {/if}
    </div>
</div>
{#if !compact}
    <Separator class="bg-border-hard" />
{/if}
{#if workflow?.file}
    <WorkflowReadOnlyBanner file={workflow.file} />
{:else if workflow?.isError}
    <p role="alert" class="text-sm text-destructive">
        Could not load the batch for this file. It stays read-only.
    </p>
{/if}
