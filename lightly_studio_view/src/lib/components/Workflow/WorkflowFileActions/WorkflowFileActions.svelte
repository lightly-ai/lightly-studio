<script lang="ts">
    import { Button, buttonVariants } from '$lib/components/ui/button';
    import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
    import Ellipsis from '@lucide/svelte/icons/ellipsis';
    import { toast } from 'svelte-sonner';
    import WorkflowOverrideDialog from './WorkflowOverrideDialog.svelte';
    import {
        placeWorkflowActions,
        type WorkflowAction,
        type WorkflowFileState,
        type WorkflowMenuAction
    } from './workflowActions';

    interface Props {
        /** The file’s current state. */
        fileState: WorkflowFileState;
        /** Target states the current user may move the file to right now. */
        allowedTransitions: WorkflowFileState[];
        /** A move is waiting for the workflow service. */
        transitioning: boolean;
        /** Moves the file; resolves once the service confirmed it. */
        onTransition: (state: WorkflowFileState) => Promise<void>;
    }

    const { fileState, allowedTransitions, transitioning, onTransition }: Props = $props();

    const actions = $derived(placeWorkflowActions(fileState, allowedTransitions));
    const hasActions = $derived(actions.inline.length > 0 || actions.menu.length > 0);

    let requested = $state<WorkflowFileState | null>(null);
    /** The admin menu action waiting for confirmation, if any. */
    let confirming = $state<WorkflowMenuAction | null>(null);

    /** A move is in flight, started here or reported by the parent. */
    const busy = $derived(transitioning || requested !== null);
    /** A confirmed menu move in flight: shown in place of the ⋯ button. */
    const pendingMenuAction = $derived(actions.menu.find((a) => a.target === requested));

    const move = async (target: WorkflowFileState) => {
        requested = target;
        try {
            await onTransition(target);
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Could not change the file state');
        } finally {
            requested = null;
        }
    };

    const confirmOverride = (action: WorkflowMenuAction) => {
        confirming = null;
        void move(action.target);
    };

    const buttonLabel = (action: WorkflowAction) =>
        requested === action.target ? action.pendingLabel : action.label;
</script>

{#if hasActions}
    <div class="flex items-center gap-3" data-testid="workflow-file-actions">
        {#each actions.inline as action (action.target)}
            <Button
                size="sm"
                variant={action.variant}
                disabled={busy}
                onclick={() => move(action.target)}>{buttonLabel(action)}</Button
            >
        {/each}
        {#if pendingMenuAction}
            <Button size="sm" variant="ghost" disabled>{pendingMenuAction.pendingLabel}</Button>
        {:else if actions.menu.length > 0}
            <DropdownMenu.Root>
                <DropdownMenu.Trigger
                    class={buttonVariants({ variant: 'ghost', size: 'icon' })}
                    aria-label="Admin actions"
                    disabled={busy}
                >
                    <Ellipsis class="size-4" />
                </DropdownMenu.Trigger>
                <DropdownMenu.Content align="end">
                    {#each actions.menu as action (action.target)}
                        <DropdownMenu.Item onSelect={() => (confirming = action)}
                            >{action.label}</DropdownMenu.Item
                        >
                    {/each}
                </DropdownMenu.Content>
            </DropdownMenu.Root>
        {/if}
    </div>
{/if}

<WorkflowOverrideDialog
    action={confirming}
    onConfirm={confirmOverride}
    onCancel={() => (confirming = null)}
/>
