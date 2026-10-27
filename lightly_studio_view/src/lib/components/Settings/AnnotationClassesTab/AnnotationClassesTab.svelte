<script lang="ts">
    import { page } from '$app/state';
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import { AnnotationClassList } from './AnnotationClassList';
    import { AnnotationClassSearchInput } from './AnnotationClassSearchInput';
    import { AnnotationClassesStatus } from './AnnotationClassesStatus';
    import { useAnnotationClasses } from './useAnnotationClasses';

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

    let query = $state('');

    const trimmedQuery = $derived(query.trim());
    const sortedClasses = $derived(
        [...(classes.query.data ?? [])].sort((a, b) =>
            a.annotation_label_name.localeCompare(b.annotation_label_name)
        )
    );
    const visibleClasses = $derived(
        sortedClasses.filter((c) =>
            c.annotation_label_name.toLowerCase().includes(trimmedQuery.toLowerCase())
        )
    );
    const exactMatch = $derived(
        sortedClasses.find(
            (c) => c.annotation_label_name.toLowerCase() === trimmedQuery.toLowerCase()
        )
    );
    const canAdd = $derived(trimmedQuery.length > 0 && !exactMatch);
    // Enter adds only when nothing matches, so a partial search like "bea" for "bear"
    // never adds a class by accident.
    const canAddWithEnter = $derived(canAdd && visibleClasses.length === 0);

    // The last added class is highlighted and scrolled into view, so the user can
    // edit it, for example its color, straight away.
    let addedId = $state<string | null>(null);

    const add = async () => {
        if (!canAdd || dialogState?.isSaving) return;
        const name = trimmedQuery;
        try {
            const created = await classes.addClass(name);
            query = '';
            addedId = created.annotation_label_id ?? null;
        } catch {
            // The hook already shows an error toast. Keep the typed name so the user can retry.
        }
    };
    // The input is inside the settings form, so Enter must not submit it.
    const onKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        if (canAddWithEnter) add();
    };
</script>

{#if !collectionId}
    <p class="text-sm text-muted-foreground">Open a dataset to manage its annotation classes.</p>
{:else}
    <!-- Only the list scrolls, so the search stays visible. -->
    <div class="flex h-full flex-col gap-3">
        <div class="mx-auto flex w-full max-w-lg shrink-0 flex-col gap-3">
            <AnnotationClassSearchInput bind:value={query} onkeydown={onKeyDown} />
            <AnnotationClassesStatus
                totalCount={sortedClasses.length}
                visibleCount={visibleClasses.length}
                searchText={trimmedQuery}
                exactMatchName={exactMatch?.annotation_label_name}
            />
        </div>
        <!-- Full width, so the scrollbar is at the dialog edge. -->
        <div
            class="-mx-6 -mb-4 min-h-0 flex-1 overflow-y-auto border-t border-border/40 px-6 pb-4 pt-1"
        >
            <AnnotationClassList
                classes={visibleClasses}
                isLoading={classes.query.isLoading}
                addName={canAdd ? trimmedQuery : ''}
                isAddEnterTarget={canAddWithEnter}
                showEmptyHint={sortedClasses.length === 0 && !canAdd}
                highlightedId={addedId}
                onAdd={add}
                onRename={classes.renameClass}
                onDelete={classes.deleteClass}
            />
        </div>
    </div>
{/if}
