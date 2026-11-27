<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { useQueryClient } from '@tanstack/svelte-query';
    import { toast } from 'svelte-sonner';
    import { QueryEditor, useQueryEditor } from '$lib/components/QueryEditor';
    import { useQueryHistory, useTags, type useImageFilters } from '$lib/hooks';

    import QueryEditorPanelHeader from './QueryEditorPanelHeader.svelte';
    import QueryHistoryMenu from './QueryHistoryMenu.svelte';

    type UpdateQueryExpr = ReturnType<typeof useImageFilters>['updateQueryExpr'];
    type QueryExpression = NonNullable<Parameters<UpdateQueryExpr>[0]>;

    interface Props {
        /** Invoked when the user clicks the close button in the panel header. */
        onClose: () => void;
        /** Collection whose tags the editor validates tag names against. */
        collectionId: string;
        sampleType: 'image' | 'video';
        queryExpression: QueryExpression | null;
        updateQueryExpr: UpdateQueryExpr;
    }

    type OnSaveHandler = ComponentProps<typeof QueryEditor>['onSave'];

    const { onClose, collectionId, sampleType, queryExpression, updateQueryExpr }: Props = $props();
    const { tags, isLoading, error } = $derived(useTags({ collection_id: collectionId }));
    // Skip the tag check until the tags are known, to avoid false warnings.
    const tagNames = $derived($isLoading || $error ? undefined : $tags.map((tag) => tag.name));
    const queryClient = useQueryClient();
    const { translateQuery } = useQueryEditor();
    const { queryHistory, addQuery } = useQueryHistory();

    // The editor reads its text only when it mounts. A new key remounts it with the applied query.
    let editorKey = $state(0);
    // A history query that does not translate anymore. The user can correct it in the editor.
    let draftQuery = $state<string>();

    const applyQuery = (query: string, queryExpr?: QueryExpression['query_expr']) => {
        updateQueryExpr(queryExpr ? { query_expr: queryExpr, query_expr_str: query } : undefined);
        if (queryExpr) addQuery(collectionId, query);
        // Data may have changed since the last apply, so refetch even if the query is unchanged.
        queryClient.invalidateQueries();
    };

    const handleQueryEditorValueChange: OnSaveHandler = (value, parsed) => {
        if (parsed.status === 'error') {
            throw new Error(`Failed to parse query expression: ${JSON.stringify(parsed.errors)}`);
        }
        applyQuery(value, parsed.status === 'empty' ? undefined : parsed.queryExpr);
    };

    const applyQueryFromHistory = (query: string) => {
        const translation = translateQuery(query, sampleType);
        editorKey += 1;
        if (translation.status === 'error') {
            toast.error('This query is not valid anymore. Edit it and apply it again.');
            draftQuery = query;
            return;
        }
        draftQuery = undefined;
        applyQuery(query, translation.status === 'empty' ? undefined : translation.queryExpr);
    };
</script>

<div class="flex h-full min-w-0 flex-1 flex-col rounded-panel bg-card p-4">
    <QueryEditorPanelHeader {sampleType} {onClose} />
    {#key editorKey}
        <QueryEditor
            height="100%"
            {sampleType}
            value={queryExpression?.query_expr_str}
            draft={draftQuery}
            {tagNames}
            onSave={handleQueryEditorValueChange}
        >
            {#snippet footerActions()}
                <QueryHistoryMenu
                    queries={$queryHistory[collectionId] ?? []}
                    onSelect={applyQueryFromHistory}
                />
            {/snippet}
        </QueryEditor>
    {/key}
</div>
