<script lang="ts">
    import { page } from '$app/state';
    import { Button } from '$lib/components';
    import { Input } from '$lib/components/ui/input';
    import { Pencil, Trash2 } from '@lucide/svelte';
    import { SettingsGroup } from '../SettingsGroup';
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import { useAnnotationClasses } from './useAnnotationClasses.svelte';

    interface Props {
        // This tab saves its changes immediately, not with the settings form.
        dialogState?: Pick<SettingsDialogState, 'isSaving'>;
    }

    const { dialogState }: Props = $props();

    const collectionId = $derived(page.params.collection_id);
    const datasetId = $derived(page.params.dataset_id);
    const classes = useAnnotationClasses(() => ({
        collectionId: collectionId ?? '',
        datasetId: datasetId ?? ''
    }));

    let newName = $state('');
    let editingId = $state<string | null>(null);
    let editingName = $state('');

    const sortedClasses = $derived(
        [...(classes.query.data ?? [])].sort((a, b) =>
            a.annotation_label_name.localeCompare(b.annotation_label_name)
        )
    );
    const trimmedNewName = $derived(newName.trim());
    const isDuplicate = $derived(
        sortedClasses.some(
            (c) => c.annotation_label_name.toLowerCase() === trimmedNewName.toLowerCase()
        )
    );

    const add = async () => {
        if (!trimmedNewName || isDuplicate) return;
        await classes.addClass(trimmedNewName);
        newName = '';
    };
    const saveRename = async () => {
        const name = editingName.trim();
        if (editingId && name) await classes.renameClass(editingId, name);
        editingId = null;
    };
    // The inputs are inside the settings form, so Enter must not submit it.
    const onEnter = (event: KeyboardEvent, action: () => void) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        action();
    };
</script>

{#if !collectionId}
    <p class="text-sm text-muted-foreground">Open a dataset to manage its annotation classes.</p>
{:else}
    <div class="space-y-6">
        <p class="text-sm text-muted-foreground">
            Annotation classes that can be used when labeling this dataset. Changes save
            immediately.
        </p>
        <SettingsGroup title="Add annotation class">
            <div class="flex gap-2 py-3">
                <Input
                    bind:value={newName}
                    placeholder="Annotation class name, for example dog"
                    aria-label="New annotation class name"
                    onkeydown={(e) => onEnter(e, add)}
                />
                <Button
                    variant="default"
                    buttonProps={{
                        type: 'button',
                        onclick: add,
                        disabled: !trimmedNewName || isDuplicate || dialogState?.isSaving
                    }}
                >
                    Add
                </Button>
            </div>
            {#if isDuplicate}
                <p class="pb-2 text-xs text-muted-foreground">This annotation class exists.</p>
            {/if}
        </SettingsGroup>
        <SettingsGroup title={`Annotation classes (${sortedClasses.length})`}>
            {#if classes.query.isLoading}
                <p class="py-3 text-sm text-muted-foreground">Loading…</p>
            {:else if sortedClasses.length === 0}
                <p class="py-3 text-sm text-muted-foreground">No annotation classes yet.</p>
            {/if}
            {#each sortedClasses as annotationClass (annotationClass.annotation_label_id)}
                <div class="flex items-center gap-2 py-2">
                    {#if editingId === annotationClass.annotation_label_id}
                        <Input
                            bind:value={editingName}
                            aria-label="Annotation class name"
                            onkeydown={(e) => onEnter(e, saveRename)}
                            onblur={saveRename}
                        />
                    {:else}
                        <span class="min-w-0 flex-1 truncate text-sm">
                            {annotationClass.annotation_label_name}
                        </span>
                        <Button
                            variant="ghost"
                            buttonProps={{
                                type: 'button',
                                title: 'Rename',
                                'aria-label': `Rename ${annotationClass.annotation_label_name}`,
                                onclick: () => {
                                    editingId = annotationClass.annotation_label_id ?? null;
                                    editingName = annotationClass.annotation_label_name;
                                }
                            }}
                        >
                            <Pencil class="size-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            buttonProps={{
                                type: 'button',
                                title: 'Delete',
                                'aria-label': `Delete ${annotationClass.annotation_label_name}`,
                                onclick: () =>
                                    classes.deleteClass(annotationClass.annotation_label_id!)
                            }}
                        >
                            <Trash2 class="size-4" />
                        </Button>
                    {/if}
                </div>
            {/each}
        </SettingsGroup>
    </div>
{/if}
