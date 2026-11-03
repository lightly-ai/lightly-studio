<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import type { Snippet } from 'svelte';

    interface Props {
        selectedCount: number;
        disabled: boolean;
        onDelete: () => Promise<void> | void;
        /** Replaces the default "Delete N annotations" button, e.g. with an icon button. */
        trigger?: Snippet<[{ props: Record<string, unknown> }]>;
    }

    let { selectedCount, disabled, onDelete, trigger }: Props = $props();

    let open = $state(false);
    const countLabel = $derived(
        `${selectedCount} ${selectedCount === 1 ? 'annotation' : 'annotations'}`
    );

    async function handleConfirm() {
        if (disabled) return;
        try {
            await onDelete();
        } finally {
            open = false;
        }
    }
</script>

<Dialog.Root bind:open>
    <Dialog.Trigger>
        {#snippet child({ props })}
            {#if trigger}
                {@render trigger({ props })}
            {:else}
                <Button
                    {...props}
                    variant="destructive"
                    class="w-full"
                    disabled={selectedCount === 0 || disabled}
                >
                    Delete {countLabel}
                </Button>
            {/if}
        {/snippet}
    </Dialog.Trigger>
    <Dialog.Content class="max-w-sm">
        <Dialog.Header>
            <Dialog.Title>Delete {countLabel}?</Dialog.Title>
            <Dialog.Description>This cannot be undone.</Dialog.Description>
        </Dialog.Header>
        <Dialog.Footer>
            <Dialog.Close>
                {#snippet child({ props })}
                    <Button {...props} variant="outline" {disabled}>Cancel</Button>
                {/snippet}
            </Dialog.Close>
            <Button variant="destructive" {disabled} onclick={handleConfirm}>Delete</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
