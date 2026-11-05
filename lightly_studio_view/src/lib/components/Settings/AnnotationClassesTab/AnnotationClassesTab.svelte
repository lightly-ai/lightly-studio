<script lang="ts">
    import { page } from '$app/state';
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import { AnnotationClassList } from './AnnotationClassList';
    import { NameListSearchInput } from '$lib/components/Settings/NameList';
    import { AnnotationClassesStatus } from './AnnotationClassesStatus';
    import { searchAnnotationClasses } from './AnnotationClassesTab.helpers';
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
    const { sortedClasses, visibleClasses, exactMatch, canAdd, canAddWithEnter } = $derived(
        searchAnnotationClasses(classes.query.data, trimmedQuery)
    );

    // The last added class is highlighted and scrolled into view, so the user can
    // edit it, for example its color, straight away.
    let addedId = $state<string | null>(null);
    // Blocks a second add of the same name before the list refreshes.
    let isAdding = false;

    const add = async () => {
        if (!canAdd || isAdding || dialogState?.isSaving) return;
        const name = trimmedQuery;
        isAdding = true;
        try {
            const created = await classes.addClass(name);
            // Keep text that the user typed while the request was pending.
            if (query.trim() === name) query = '';
            addedId = created.annotation_label_id ?? null;
        } catch {
            // The hook already shows an error toast. Keep the typed name so the user can retry.
        } finally {
            isAdding = false;
        }
    };
    // The input is inside the settings form, so Enter must not submit it.
    // Enter while an IME composes text confirms the text. Safari sends that Enter with
    // isComposing false and keyCode 229.
    const onKeyDown = (event: KeyboardEvent) => {
        const isComposing = event.isComposing || event.keyCode === 229;
        if (event.key !== 'Enter' || isComposing) return;
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
            <NameListSearchInput
                bind:value={query}
                onkeydown={onKeyDown}
                label="Find or add an annotation class"
            />
            <AnnotationClassesStatus
                totalCount={sortedClasses.length}
                visibleCount={visibleClasses.length}
                searchText={trimmedQuery}
                exactMatchName={exactMatch?.annotation_label_name}
                isLoading={classes.query.isLoading}
            />
        </div>
        <!-- Full width, so the scrollbar is at the dialog edge. -->
        <div
            class="-mx-6 -mb-4 min-h-0 flex-1 overflow-y-auto border-t border-border/40 px-6 pb-4 pt-1"
        >
            <AnnotationClassList
                classes={visibleClasses}
                isLoading={classes.query.isLoading}
                isError={classes.query.isError}
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
