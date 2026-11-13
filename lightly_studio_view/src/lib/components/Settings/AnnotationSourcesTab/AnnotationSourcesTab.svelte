<script lang="ts">
    import { page } from '$app/state';
    import { AnnotationSourceList } from './AnnotationSourceList';
    import { DeleteAnnotationSourceDialog } from './DeleteAnnotationSourceDialog';
    import { useAnnotationSources } from './useAnnotationSources';
    import { useFollowShownSource } from './useFollowShownSource';
    import type { SettingsDialogState } from '../settingsDialogState.svelte';

    interface Props {
        // Every settings tab gets the dialog state. This tab saves its changes immediately.
        dialogState?: Pick<SettingsDialogState, 'isSaving'>;
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { dialogState: _dialogState }: Props = $props();

    // Any collection of the dataset lists every annotation source of the dataset.
    const routeCollectionId = $derived(page.params.collection_id ?? '');
    const sources = useAnnotationSources(() => ({ collectionId: routeCollectionId }));
    const isError = $derived(sources.query.isError);
    const isLoading = $derived(!isError && sources.query.isLoading);
    const sortedSources = $derived(
        [...(sources.query.data ?? [])].sort((a, b) => a.name.localeCompare(b.name))
    );
    const followShownSource = useFollowShownSource(() => ({ routeCollectionId }));

    let deleting = $state<{
        id: string;
        name: string;
        annotationCount: number;
        collectionId: string;
    } | null>(null);
    const sourceCount = $derived(sortedSources.length);
</script>

{#if !routeCollectionId}
    <p class="text-sm text-muted-foreground">Open a dataset to manage its annotation sources.</p>
{:else}
    <div class="flex h-full flex-col gap-3">
        <p class="mx-auto min-h-4 w-full max-w-lg shrink-0 px-2 text-xs text-muted-foreground">
            {#if !isLoading && !isError}
                {sourceCount} annotation {sourceCount === 1 ? 'source' : 'sources'}
            {/if}
        </p>
        <div
            class="-mx-6 -mb-4 min-h-0 flex-1 overflow-y-auto border-t border-border/40 px-6 pb-4 pt-1"
        >
            <AnnotationSourceList
                sources={sortedSources}
                {isLoading}
                {isError}
                onDelete={(source) =>
                    (deleting = {
                        id: source.collection_id,
                        name: source.name,
                        annotationCount: source.annotation_count,
                        collectionId: source.parent_collection_id
                    })}
            />
        </div>
    </div>
    {#if deleting}
        <DeleteAnnotationSourceDialog
            collectionId={deleting.collectionId}
            source={deleting}
            onClose={() => (deleting = null)}
            onDeleted={followShownSource.afterDelete}
        />
    {/if}
{/if}
