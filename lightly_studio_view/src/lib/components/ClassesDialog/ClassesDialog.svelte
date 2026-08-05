<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import { useClasses } from '$lib/hooks/useClasses/useClasses.svelte';
    import { useClassesDialog } from '$lib/hooks/useClassesDialog/useClassesDialog';
    import AddClassesForm from './AddClassesForm.svelte';
    import ClassesDialogTable from './ClassesDialogTable.svelte';

    let { collectionId }: { collectionId: string } = $props();
    const { isClassesDialogOpen, openClassesDialog, closeClassesDialog } = useClassesDialog();
    const { query, addClasses } = useClasses(() => ({
        collectionId,
        enabled: $isClassesDialogOpen
    }));
    const skeletonRows = [0, 1, 2];

    let searchTerm = $state('');
    const filteredLabels = $derived.by(() => {
        const term = searchTerm.trim().toLowerCase();
        const labels = query.data ?? [];
        if (!term || term.includes(',')) return labels;
        return labels.filter((l) => l.annotation_label_name.toLowerCase().includes(term));
    });

    function setOpen(open: boolean) {
        if (open) {
            openClassesDialog();
        } else {
            closeClassesDialog();
            searchTerm = '';
        }
    }
</script>

<Dialog.Root open={$isClassesDialogOpen} onOpenChange={setOpen}>
    <Dialog.Content class="border-border bg-background sm:max-w-[620px]">
        <Dialog.Header>
            <Dialog.Title>Classes</Dialog.Title>
            <Dialog.Description>
                Define the annotation classes available during labeling.
            </Dialog.Description>
        </Dialog.Header>

        <AddClassesForm
            existingNames={(query.data ?? []).map((label) => label.annotation_label_name)}
            onAdd={addClasses}
            onValueChange={(v) => (searchTerm = v)}
        />

        {#if query.isPending}
            <div class="space-y-2 py-4" aria-label="Loading classes">
                {#each skeletonRows as row (row)}
                    <div class="h-10 animate-pulse rounded bg-muted"></div>
                {/each}
            </div>
        {:else if query.isError}
            <p class="py-6 text-center text-sm text-destructive" role="alert">
                Failed to load classes. Please try again.
            </p>
        {:else}
            <ClassesDialogTable labels={filteredLabels} />
        {/if}
    </Dialog.Content>
</Dialog.Root>
