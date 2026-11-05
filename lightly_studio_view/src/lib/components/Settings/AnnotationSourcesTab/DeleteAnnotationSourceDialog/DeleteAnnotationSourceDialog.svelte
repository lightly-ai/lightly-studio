<script lang="ts">
    import { Button } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';
    import { useDeleteAnnotationSource } from './useDeleteAnnotationSource.svelte';

    interface Props {
        /** The collection that owns the annotation sources. */
        collectionId: string;
        source: { id: string; name: string; annotationCount: number };
        /** Called when the dialog closes, after a delete or a cancel. */
        onClose: () => void;
        /** Called after the delete, before `onClose`. */
        onDeleted?: () => void;
    }
    const { collectionId, source, onClose, onDeleted }: Props = $props();
    const { mutation, remove } = useDeleteAnnotationSource(() => ({
        collectionId,
        source,
        onDeleted: () => {
            onDeleted?.();
            onClose();
        }
    }));
    const countText = $derived(
        `its ${source.annotationCount} annotation${source.annotationCount === 1 ? '' : 's'}`
    );
</script>

<Dialog.Root
    bind:open={
        () => true,
        (value) => {
            if (!value && !mutation.isPending) onClose();
        }
    }
>
    <Dialog.Content>
        <Dialog.Header>
            <Dialog.Title>Delete annotation source?</Dialog.Title>
            <Dialog.Description>
                Delete “{source.name}” and {countText}? This cannot be undone. An annotation source
                that evaluation runs use cannot be deleted. Delete those runs first.
            </Dialog.Description>
        </Dialog.Header>
        <Dialog.Footer>
            <Button
                variant="outline"
                buttonProps={{ disabled: mutation.isPending, onclick: onClose }}>Cancel</Button
            >
            <Button
                variant="destructive"
                isPending={mutation.isPending}
                buttonProps={{ onclick: remove }}
            >
                {mutation.isPending ? 'Deleting…' : 'Delete'}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
