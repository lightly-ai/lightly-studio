<script lang="ts">
    import { Button, buttonVariants } from '$lib/components/ui/button';
    import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import Ellipsis from '@lucide/svelte/icons/ellipsis';
    import WorkflowOverrideDialog from './WorkflowOverrideDialog.svelte';
    import {
        placeWorkflowActions,
        type WorkflowAction,
        type WorkflowFileState,
        type WorkflowMenuAction
    } from './workflowActions';
    import { useWorkflowMove } from './useWorkflowMove.svelte';

    interface Props {
        /** The file’s current state. */
        fileState: WorkflowFileState;
        /** Target states the current user may move the file to right now. */
        allowedTransitions: WorkflowFileState[];
        /** A move is waiting for the workflow service. */
        transitioning: boolean;
        /** Moves the file; resolves once the service confirmed it. */
        onTransition: (state: WorkflowFileState) => Promise<void>;
        /** Opens the next sample; called after a successful inline move, not an admin override. */
        onAdvance?: () => void;
    }

    const { fileState, allowedTransitions, transitioning, onTransition, onAdvance }: Props =
        $props();

    const actions = $derived(placeWorkflowActions(fileState, allowedTransitions));
    const hasActions = $derived(actions.inline.length > 0 || actions.menu.length > 0);

    const workflowMove = useWorkflowMove(() => ({ onTransition, onAdvance }));
    const requested = $derived(workflowMove.requested);
    /** The admin menu action waiting for confirmation, if any. */
    let confirming = $state<WorkflowMenuAction | null>(null);

    /** A move is in flight, started here or reported by the parent. */
    const busy = $derived(transitioning || requested !== null);
    /** A confirmed menu move in flight: shown in place of the ⋯ button. */
    const pendingMenuAction = $derived(actions.menu.find((a) => a.target === requested));

    const confirmOverride = (action: WorkflowMenuAction) => {
        confirming = null;
        workflowMove.override(action.target);
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
                class={action.class}
                disabled={busy}
                onclick={() => workflowMove.moveAndAdvance(action)}>{buttonLabel(action)}</Button
            >
        {/each}
        {#if pendingMenuAction}
            <Button size="sm" variant="ghost" disabled>{pendingMenuAction.pendingLabel}</Button>
        {:else if actions.menu.length > 0}
            <Tooltip content="Admin actions" position="bottom" noTriggerRole>
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
            </Tooltip>
        {/if}
    </div>
{/if}

<WorkflowOverrideDialog
    action={confirming}
    onConfirm={confirmOverride}
    onCancel={() => (confirming = null)}
/>
