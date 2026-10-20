<script lang="ts">
    import { Button } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Trash2 } from '@lucide/svelte';
    import { useDeleteEvaluationRun } from './useDeleteEvaluationRun.svelte';

    interface Props {
        datasetId: string;
        run: { id: string; name: string };
    }
    const { datasetId, run }: Props = $props();
    let open = $state(false);
    const { mutation, remove } = useDeleteEvaluationRun(() => ({
        datasetId,
        run,
        onSuccess: () => (open = false)
    }));
</script>

<Button
    icon={Trash2}
    ariaLabel={`Delete evaluation ${run.name}`}
    buttonProps={{ size: 'icon', title: 'Delete evaluation', onclick: () => (open = true) }}
/>
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
            <Dialog.Title>Delete evaluation?</Dialog.Title>
            <Dialog.Description>
                Delete “{run.name}” and its results? Annotations will be kept. This cannot be
                undone.
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
