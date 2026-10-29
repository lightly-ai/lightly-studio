<script lang="ts">
    import { Button } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';
    import { useDeleteAnnotationSource } from './useDeleteAnnotationSource.svelte';

    interface Props {
        collectionId: string;
        source: { id: string; name: string };
        /** Called when the dialog closes, after a delete or a cancel. */
        onClose: () => void;
    }
    const { collectionId, source, onClose }: Props = $props();
    const { mutation, remove, annotationCount } = useDeleteAnnotationSource(() => ({
        collectionId,
        source,
        onDeleted: onClose
    }));
    const count = $derived(annotationCount());
    const countText = $derived(
        count === undefined
            ? 'all its annotations'
            : `its ${count} annotation${count === 1 ? '' : 's'}`
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
                Delete “{source.name}” and {countText}? This cannot be undone.
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
