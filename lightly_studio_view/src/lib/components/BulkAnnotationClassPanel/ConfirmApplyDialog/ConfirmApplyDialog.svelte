<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import { Button } from '$lib/components';

    interface Props {
        open: boolean;
        /** Annotation class about to be added to the selection. */
        className: string;
        /** Annotation source the new annotations are written to. */
        source: string;
        /** Number of selected images. */
        imageCount: number;
        isApplying: boolean;
        onOpenChange: (open: boolean) => void;
        onConfirm: () => void;
    }

    const { open, className, source, imageCount, isApplying, onOpenChange, onConfirm }: Props =
        $props();
</script>

<Dialog.Root {open} {onOpenChange}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[440px]">
            <Dialog.Header>
                <Dialog.Title class="text-foreground">Add class</Dialog.Title>
                <Dialog.Description class="text-foreground">
                    Add <span class="font-semibold">{className}</span> to
                    {imageCount}
                    {imageCount === 1 ? 'image' : 'images'} in
                    <span class="font-semibold">{source}</span>. This cannot be undone.
                </Dialog.Description>
            </Dialog.Header>

            <Dialog.Footer>
                <Button
                    variant="outline"
                    buttonProps={{
                        type: 'button',
                        onclick: () => onOpenChange(false),
                        disabled: isApplying,
                        'data-testid': 'confirm-apply-cancel'
                    }}
                >
                    Cancel
                </Button>
                <Button
                    variant="default"
                    isPending={isApplying}
                    buttonProps={{
                        type: 'button',
                        onclick: onConfirm,
                        disabled: isApplying,
                        'data-testid': 'confirm-apply-submit'
                    }}
                >
                    Add class
                </Button>
            </Dialog.Footer>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
