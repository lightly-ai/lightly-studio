<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { X } from '@lucide/svelte';
    import { useQueryClient } from '@tanstack/svelte-query';
    import QueryEditor from '$lib/components/QueryEditor/QueryEditor.svelte';
    import { Button } from '$lib/components';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import type { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';

    import QuerySyntaxHelp from './QuerySyntaxHelp.svelte';

    interface Props {
        /** Invoked when the user clicks the close button in the panel header. */
        onClose: () => void;
        sampleType: 'image' | 'video';
        queryExpression:
            | Parameters<ReturnType<typeof useImageFilters>['updateQueryExpr']>[0]
            | null;
        updateQueryExpr: ReturnType<typeof useImageFilters>['updateQueryExpr'];
    }

    type OnSaveHandler = ComponentProps<typeof QueryEditor>['onSave'];

    const { onClose, sampleType, queryExpression, updateQueryExpr }: Props = $props();
    const queryClient = useQueryClient();

    const handleQueryEditorValueChange: OnSaveHandler = (value, parsed) => {
        if (!parsed) {
            throw new Error('Failed to parse query expression');
        }
        if (parsed.status === 'error') {
            throw new Error(`Failed to parse query expression: ${JSON.stringify(parsed.errors)}`);
        }
        updateQueryExpr({
            query_expr: parsed.queryExpr,
            query_expr_str: value
        });
        // Data may have changed since the last apply, so refetch even if the query is unchanged.
        queryClient.invalidateQueries();
    };
</script>

<div class="flex h-full min-w-0 flex-1 flex-col rounded-[1vw] bg-card p-4">
    <div class="mb-3 min-w-0">
        <div class="flex items-center justify-between">
            <Typography variant="h5" component="h2" className="text-foreground"
                >Query Filter</Typography
            >
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
        <QuerySyntaxHelp {sampleType} />
    </div>
    <QueryEditor
        height="100%"
        {sampleType}
        value={queryExpression?.query_expr_str}
        onSave={handleQueryEditorValueChange}
    />
</div>
