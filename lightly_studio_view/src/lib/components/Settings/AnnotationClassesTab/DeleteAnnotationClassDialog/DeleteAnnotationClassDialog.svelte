<script lang="ts">
    import { Button } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';
    import { formatInteger } from '$lib/utils';

    interface Props {
        open: boolean;
        name: string;
        annotationCount: number;
        onConfirm: () => Promise<unknown>;
    }

    let { open = $bindable(), name, annotationCount, onConfirm }: Props = $props();

    let isDeleting = $state(false);

    const annotationsText = $derived(
        `${formatInteger(annotationCount)} ${annotationCount === 1 ? 'annotation' : 'annotations'}`
    );

    // Keep the dialog open while the deletion runs. Closing it would not stop the request.
    const setOpen = (value: boolean) => {
        if (!isDeleting) {
            open = value;
        }
    };

    const confirm = async () => {
        isDeleting = true;
        try {
            await onConfirm();
            open = false;
        } catch {
            // The caller reports the failure. Keep the dialog open.
        } finally {
            isDeleting = false;
        }
    };
</script>

<Dialog.Root bind:open={() => open, setOpen}>
    <Dialog.Content class="border-border bg-background sm:max-w-md">
        <Dialog.Header>
            <Dialog.Title class="text-foreground">
                Delete annotation class "{name}"?
            </Dialog.Title>
            <Dialog.Description>
                {#if annotationCount > 0}
                    This also deletes
                    <strong class="font-semibold text-primary">{annotationsText}</strong> of this class.
                    Evaluation runs that use these annotations become out of date. You cannot undo this.
                {:else}
                    No annotations use this class. You cannot undo this.
                {/if}
            </Dialog.Description>
        </Dialog.Header>
        <Dialog.Footer class="gap-2">
            <Button
                variant="outline"
                buttonProps={{
                    type: 'button',
                    disabled: isDeleting,
                    onclick: () => setOpen(false)
                }}
            >
                Cancel
            </Button>
            <Button
                variant="destructive"
                isPending={isDeleting}
                buttonProps={{ type: 'button', onclick: confirm }}
            >
                {#if annotationCount > 0}
                    Delete class and {annotationsText}
                {:else}
                    Delete annotation class
                {/if}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
