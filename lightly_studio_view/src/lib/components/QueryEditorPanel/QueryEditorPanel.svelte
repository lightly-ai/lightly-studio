<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import X from '@lucide/svelte/icons/x';
    import { useQueryClient } from '@tanstack/svelte-query';
    import { toast } from 'svelte-sonner';
    import QueryEditor from '$lib/components/QueryEditor/QueryEditor.svelte';
    import { useQueryEditor } from '$lib/components/QueryEditor/useQueryEditor';
    import { Button } from '$lib/components';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import type { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useQueryHistory } from '$lib/hooks';

    import QueryHistoryMenu from './QueryHistoryMenu.svelte';
    import QuerySyntaxHelp from './QuerySyntaxHelp.svelte';

    type UpdateQueryExpr = ReturnType<typeof useImageFilters>['updateQueryExpr'];
    type QueryExpression = NonNullable<Parameters<UpdateQueryExpr>[0]>;

    interface Props {
        /** Invoked when the user clicks the close button in the panel header. */
        onClose: () => void;
        collectionId: string;
        sampleType: 'image' | 'video';
        queryExpression: QueryExpression | null;
        updateQueryExpr: UpdateQueryExpr;
    }

    type OnSaveHandler = ComponentProps<typeof QueryEditor>['onSave'];

    const { onClose, collectionId, sampleType, queryExpression, updateQueryExpr }: Props = $props();
    const queryClient = useQueryClient();
    const { translateQuery } = useQueryEditor();
    const { queryHistory, addQuery } = useQueryHistory();

    // The editor reads its text only when it mounts. A new key remounts it with the applied query.
    let editorKey = $state(0);

    const applyQuery = (query: string, queryExpr: QueryExpression['query_expr']) => {
        updateQueryExpr({ query_expr: queryExpr, query_expr_str: query });
        addQuery(collectionId, query);
        // Data may have changed since the last apply, so refetch even if the query is unchanged.
        queryClient.invalidateQueries();
    };

    const handleQueryEditorValueChange: OnSaveHandler = (value, parsed) => {
        if (!parsed) {
            throw new Error('Failed to parse query expression');
        }
        if (parsed.status === 'error') {
            throw new Error(`Failed to parse query expression: ${JSON.stringify(parsed.errors)}`);
        }
        applyQuery(value, parsed.queryExpr);
    };

    const applyQueryFromHistory = (query: string) => {
        const translation = translateQuery(query, sampleType);
        if (translation.status === 'error') {
            toast.error('This query is not valid anymore. Edit it and apply it again.');
            return;
        }
        applyQuery(query, translation.queryExpr);
        editorKey += 1;
    };
</script>

<div class="flex h-full min-w-0 flex-1 flex-col rounded-[1vw] bg-card p-4">
    <div class="mb-3 min-w-0">
        <div class="flex items-center justify-between">
            <Typography variant="h5" component="h2" className="text-foreground"
                >Query Filter</Typography
            >
            <div class="flex items-center gap-1">
                <QueryHistoryMenu
                    queries={$queryHistory[collectionId] ?? []}
                    onSelect={applyQueryFromHistory}
                />
                <Button
                    icon={X}
                    variant="ghost"
                    ariaLabel="Close query filter panel"
                    buttonProps={{
                        size: 'icon',
                        onclick: onClose,
                        class: 'h-8 w-8',
                        'data-testid': 'query-editor-close-button'
                    }}
                />
            </div>
        </div>
        <QuerySyntaxHelp {sampleType} />
    </div>
    {#key editorKey}
        <QueryEditor
            height="100%"
            {sampleType}
            value={queryExpression?.query_expr_str}
            onSave={handleQueryEditorValueChange}
        />
    {/key}
</div>
