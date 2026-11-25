<script lang="ts">
    import { Button } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';

    interface Props {
        open: boolean;
        trackLabel: string;
        annotationCount: number;
        onConfirm: () => Promise<unknown>;
    }

    let { open = $bindable(), trackLabel, annotationCount, onConfirm }: Props = $props();

    let isDeleting = $state(false);
    const countText = $derived(
        `${annotationCount} ${annotationCount === 1 ? 'cuboid' : 'cuboids'}`
    );

    // Keep the dialog open while the deletion runs. Closing it would not stop the request.
    const setOpen = (value: boolean) => {
        if (!isDeleting) open = value;
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
            <Dialog.Title class="text-foreground">Delete "{trackLabel}"?</Dialog.Title>
            <Dialog.Description>
                This also deletes
                <strong class="font-semibold text-primary">{countText}</strong>
                of this track from the 3D scene. You cannot undo this.
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
                Delete track and {countText}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
