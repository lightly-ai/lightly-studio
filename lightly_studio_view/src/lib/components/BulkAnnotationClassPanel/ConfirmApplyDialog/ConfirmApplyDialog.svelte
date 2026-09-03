<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import { Button } from '$lib/components';

    interface Props {
        open: boolean;
        /** Annotation class about to be added to the selection. */
        className: string;
        /** Annotation source the new annotations are written to. */
        source: string;
        /** Selected images that gain the annotation class. */
        affectedCount: number;
        /** Selected images that already have the annotation class. */
        skippedCount: number;
        isApplying: boolean;
        onOpenChange: (open: boolean) => void;
        onConfirm: () => void;
    }

    const {
        open,
        className,
        source,
        affectedCount,
        skippedCount,
        isApplying,
        onOpenChange,
        onConfirm
    }: Props = $props();

    const images = (count: number) => `${count} ${count === 1 ? 'image' : 'images'}`;
</script>

<Dialog.Root {open} {onOpenChange}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[440px]">
            <Dialog.Header>
                <Dialog.Title class="text-foreground">Add annotation class</Dialog.Title>
                <Dialog.Description class="text-foreground">
                    Add the annotation class <span class="font-semibold">{className}</span> to
                    {images(affectedCount)} in the annotation source
                    <span class="font-semibold">{source}</span>.
                </Dialog.Description>
            </Dialog.Header>

            <p class="text-sm text-muted-foreground" data-testid="confirm-apply-skipped">
                {#if skippedCount > 0}
                    {images(skippedCount)} already have this annotation class and are skipped.
                {:else}
                    None of the selected images have this annotation class yet.
                {/if}
            </p>
            <p class="text-xs text-muted-foreground">
                Existing annotations are kept. This cannot be undone.
            </p>

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
                        disabled: isApplying || affectedCount === 0,
                        'data-testid': 'confirm-apply-submit'
                    }}
                >
                    Add annotation class
                </Button>
            </Dialog.Footer>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
