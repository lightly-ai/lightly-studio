<script lang="ts">
    import { Button } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';

    interface Props {
        selectedCount: number;
        sourceName?: string;
        className?: string;
        canApply: boolean;
        isApplying: boolean;
        onApply: () => Promise<void> | void;
    }

    let { selectedCount, sourceName, className, canApply, isApplying, onApply }: Props = $props();

    let open = $state(false);
    let isConfirming = $state(false);
    const canConfirm = $derived(canApply && !isConfirming);
    const triggerDisabledReason = $derived(
        isApplying
            ? 'Applying annotation class…'
            : !canApply
              ? 'Select at least one sample to apply this annotation class.'
              : ''
    );

    async function handleConfirm() {
        if (!canConfirm) return;

        isConfirming = true;
        try {
            await onApply();
        } catch {
            // onApply reports its own failures.
        } finally {
            isConfirming = false;
            open = false;
        }
    }
</script>

<Dialog.Root bind:open>
    <Dialog.Trigger>
        {#snippet child({ props })}
            <Button
                variant="default"
                disabledReason={triggerDisabledReason}
                buttonProps={{ ...props, class: 'w-full' }}
            >
                Add annotation class
            </Button>
        {/snippet}
    </Dialog.Trigger>
    <Dialog.Content class="max-w-sm">
        <Dialog.Header>
            <Dialog.Title>Add annotation class</Dialog.Title>
            <Dialog.Description>
                Add <strong>{className}</strong> to {selectedCount}
                {selectedCount === 1 ? ' image ' : ' images '} in
                <strong>{sourceName}</strong>. This cannot be undone.
            </Dialog.Description>
        </Dialog.Header>
        <Dialog.Footer>
            <Dialog.Close>
                {#snippet child({ props })}
                    <Button
                        variant="outline"
                        disabledReason={isApplying ? 'Applying annotation class…' : ''}
                        buttonProps={{ ...props }}
                    >
                        Cancel
                    </Button>
                {/snippet}
            </Dialog.Close>
            <Button
                variant="default"
                disabledReason={!canConfirm ? 'Applying annotation class…' : ''}
                onclick={handleConfirm}
            >
                Add annotation class
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
