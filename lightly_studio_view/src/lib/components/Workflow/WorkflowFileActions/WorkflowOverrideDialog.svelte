<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import type { WorkflowMenuAction } from './workflowActions';

    interface Props {
        /** The admin menu action waiting for confirmation; the dialog is open while set. */
        action: WorkflowMenuAction | null;
        onConfirm: (action: WorkflowMenuAction) => void;
        onCancel: () => void;
    }

    const { action, onConfirm, onCancel }: Props = $props();
</script>

<Dialog.Root
    open={action !== null}
    onOpenChange={(open) => {
        if (!open) onCancel();
    }}
>
    {#if action}
        <Dialog.Content class="max-w-md">
            <Dialog.Header>
                <Dialog.Title>{action.confirmation.title}</Dialog.Title>
                <Dialog.Description>{action.confirmation.description}</Dialog.Description>
            </Dialog.Header>
            <Dialog.Footer>
                <Button variant="outline" onclick={onCancel}>Cancel</Button>
                <Button onclick={() => onConfirm(action)}>{action.confirmation.confirmLabel}</Button
                >
            </Dialog.Footer>
        </Dialog.Content>
    {/if}
</Dialog.Root>
