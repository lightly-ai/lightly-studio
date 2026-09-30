<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';

    interface Props {
        selectedCount: number;
        onDelete: () => Promise<void> | void;
    }

    let { selectedCount, onDelete }: Props = $props();

    let open = $state(false);
    let isDeleting = $state(false);
    const annotationWord = $derived(selectedCount === 1 ? 'annotation' : 'annotations');

    async function handleConfirm() {
        isDeleting = true;
        try {
            await onDelete();
        } catch {
            // onDelete reports its own failures.
        } finally {
            isDeleting = false;
            open = false;
        }
    }
</script>

<Dialog.Root bind:open>
    <Dialog.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="destructive"
                class="w-full"
                disabled={selectedCount === 0}
                data-testid="delete-annotations-trigger"
            >
                Delete annotations
            </Button>
        {/snippet}
    </Dialog.Trigger>
    <Dialog.Content class="max-w-sm">
        <Dialog.Header>
            <Dialog.Title>Delete annotations</Dialog.Title>
            <Dialog.Description>
                {`Delete ${selectedCount} ${annotationWord}? This cannot be undone.`}
            </Dialog.Description>
        </Dialog.Header>
        <Dialog.Footer>
            <Dialog.Close>
                {#snippet child({ props })}
                    <Button {...props} variant="outline" disabled={isDeleting}>Cancel</Button>
                {/snippet}
            </Dialog.Close>
            <Button
                variant="destructive"
                disabled={isDeleting}
                onclick={handleConfirm}
                data-testid="confirm-delete-annotations"
            >
                Delete
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
