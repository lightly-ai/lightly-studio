<script lang="ts">
    import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
    import {
        deleteCollectionMutation,
        readCollectionOptions
    } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Button } from '$lib/components/ui/button';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { toast } from 'svelte-sonner';

    interface Props {
        source: { id: string; name: string };
        onClose: () => void;
    }
    const { source, onClose }: Props = $props();
    const client = useQueryClient();
    const { selectedCollectionIds, setSelectedCollectionIds } = useAnnotationCollectionsFilter();
    const details = createQuery(() =>
        readCollectionOptions({ path: { collection_id: source.id } })
    );
    const deletion = createMutation(() => deleteCollectionMutation());

    async function deleteSource() {
        try {
            await deletion.mutateAsync({ path: { collection_id: source.id } });
            setSelectedCollectionIds($selectedCollectionIds.filter((id) => id !== source.id));
            await client.invalidateQueries();
            toast.success('Annotation source deleted');
            onClose();
        } catch {
            toast.error('Could not delete annotation source. Please try again.');
        }
    }
</script>

<Dialog.Root
    open
    onOpenChange={(open) => {
        if (!open && !deletion.isPending) onClose();
    }}
>
    <Dialog.Content>
        <Dialog.Header>
            <Dialog.Title>Delete annotation source?</Dialog.Title>
            <Dialog.Description>
                {#if details.data}
                    Delete "{source.name}" and its {details.data.total_sample_count} annotations? Images
                    will be kept. This cannot be undone.
                {:else if details.isError}
                    Could not load the annotation count for "{source.name}".
                {:else}
                    Loading annotation count for "{source.name}"...
                {/if}
            </Dialog.Description>
        </Dialog.Header>
        <Dialog.Footer>
            <Button variant="outline" onclick={onClose} disabled={deletion.isPending}>Cancel</Button
            >
            <Button
                variant="destructive"
                onclick={deleteSource}
                disabled={!details.data || deletion.isPending}
            >
                {deletion.isPending ? 'Deleting...' : 'Delete source'}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
