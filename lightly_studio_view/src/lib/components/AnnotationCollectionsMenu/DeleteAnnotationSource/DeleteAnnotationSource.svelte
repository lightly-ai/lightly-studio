<script lang="ts">
    import { Button } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Trash2 } from '@lucide/svelte';
    import { useDeleteAnnotationSource } from './useDeleteAnnotationSource.svelte';

    interface Props {
        collectionId: string;
        source: { id: string; name: string };
    }
    const { collectionId, source }: Props = $props();
    let open = $state(false);
    const { mutation, remove, annotationCount } = useDeleteAnnotationSource(() => ({
        collectionId,
        source,
        open,
        onDeleted: () => (open = false)
    }));
    const count = $derived(annotationCount());
    const countText = $derived(
        count === undefined
            ? 'all its annotations'
            : `its ${count} annotation${count === 1 ? '' : 's'}`
    );
</script>

<button
    type="button"
    class="inline-flex size-6 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
    aria-label={`Delete annotation source ${source.name}`}
    title="Delete annotation source"
    onclick={() => (open = true)}
>
    <Trash2 class="size-3.5" />
</button>
<Dialog.Root
    bind:open={
        () => open,
        (value) => {
            if (!mutation.isPending) open = value;
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
                buttonProps={{ disabled: mutation.isPending, onclick: () => (open = false) }}
                >Cancel</Button
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
