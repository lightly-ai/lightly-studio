<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import type { WorkflowActionConfirmation } from './workflowActions';

    interface Props {
        /** What the user confirms; the dialog is open while set. */
        confirmation: WorkflowActionConfirmation | null;
        onConfirm: () => void;
        onCancel: () => void;
    }

    const { confirmation, onConfirm, onCancel }: Props = $props();
</script>

<!-- Bound both ways: a close from inside the dialog (Escape, the close button, a click
     outside) must clear the waiting move, or picking it again would not reopen the dialog. -->
<Dialog.Root
    bind:open={
        () => confirmation !== null,
        (open) => {
            if (!open) onCancel();
        }
    }
>
    {#if confirmation}
        <Dialog.Content class="max-w-md">
            <Dialog.Header>
                <Dialog.Title>{confirmation.title}</Dialog.Title>
                <Dialog.Description>{confirmation.description}</Dialog.Description>
            </Dialog.Header>
            <Dialog.Footer>
                <Button variant="outline" onclick={onCancel}>Cancel</Button>
                <Button onclick={onConfirm}>{confirmation.confirmLabel}</Button>
            </Dialog.Footer>
        </Dialog.Content>
    {/if}
</Dialog.Root>
