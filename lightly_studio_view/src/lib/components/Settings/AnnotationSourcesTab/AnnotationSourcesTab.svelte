<script lang="ts">
    import { page } from '$app/state';
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import { AnnotationSourceList } from './AnnotationSourceList';
    import { AnnotationSourceSearchInput } from './AnnotationSourceSearchInput';
    import { DeleteAnnotationSourceDialog } from './DeleteAnnotationSourceDialog';
    import { searchAnnotationSources } from './AnnotationSourcesTab.helpers';
    import { useAnnotationSources } from './useAnnotationSources';

    interface Props {
        // This tab saves its changes immediately, not with the settings form.
        dialogState?: Pick<SettingsDialogState, 'isSaving'>;
    }

    const { dialogState }: Props = $props();

    const collectionId = $derived(page.params.collection_id ?? '');
    const sources = useAnnotationSources(() => ({ collectionId }));

    let query = $state('');
    const trimmedQuery = $derived(query.trim());
    const { sortedSources, visibleSources, canAdd, canAddWithEnter } = $derived(
        searchAnnotationSources(sources.query.data, trimmedQuery)
    );

    // The last added source is highlighted and scrolled into view.
    let addedId = $state<string | null>(null);
    let isAdding = false;
    let deleting = $state<{ id: string; name: string; annotationCount: number } | null>(null);

    const add = async () => {
        if (!canAdd || isAdding || dialogState?.isSaving) return;
        const name = trimmedQuery;
        isAdding = true;
        try {
            const created = await sources.addSource(name);
            if (query.trim() === name) query = '';
            addedId = created.collection_id;
        } catch {
            // The hook already shows an error toast. Keep the typed name so the user can retry.
        } finally {
            isAdding = false;
        }
    };
    // The input is inside the settings form, so Enter must not submit it.
    const onKeyDown = (event: KeyboardEvent) => {
        const isComposing = event.isComposing || event.keyCode === 229;
        if (event.key !== 'Enter' || isComposing) return;
        event.preventDefault();
        if (canAddWithEnter) add();
    };
</script>

{#if !collectionId}
    <p class="text-sm text-muted-foreground">Open a dataset to manage its annotation sources.</p>
{:else}
    <div class="flex h-full flex-col gap-3">
        <div class="mx-auto flex w-full max-w-lg shrink-0 flex-col gap-3">
            <AnnotationSourceSearchInput bind:value={query} onkeydown={onKeyDown} />
            <p class="min-h-4 px-2 text-xs text-muted-foreground">
                {#if !sources.query.isLoading}
                    {sortedSources.length} annotation {sortedSources.length === 1
                        ? 'source'
                        : 'sources'}
                {/if}
            </p>
        </div>
        <div
            class="-mx-6 -mb-4 min-h-0 flex-1 overflow-y-auto border-t border-border/40 px-6 pb-4 pt-1"
        >
            <AnnotationSourceList
                sources={visibleSources}
                isLoading={sources.query.isLoading}
                isError={sources.query.isError}
                addName={canAdd ? trimmedQuery : ''}
                isAddEnterTarget={canAddWithEnter}
                highlightedId={addedId}
                onAdd={add}
                onRename={(source, name) =>
                    sources.renameSource({ id: source.collection_id, name: source.name }, name)}
                onDelete={(source) =>
                    (deleting = {
                        id: source.collection_id,
                        name: source.name,
                        annotationCount: source.annotation_count
                    })}
            />
        </div>
    </div>
    <DeleteAnnotationSourceDialog
        {collectionId}
        source={deleting}
        onClose={() => (deleting = null)}
    />
{/if}
