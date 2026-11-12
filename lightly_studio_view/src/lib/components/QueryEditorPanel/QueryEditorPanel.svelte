<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { X } from '@lucide/svelte';
    import { useQueryClient } from '@tanstack/svelte-query';
    import QueryEditor from '$lib/components/QueryEditor/QueryEditor.svelte';
    import { Button } from '$lib/components';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useTags } from '$lib/hooks/useTags/useTags';

    interface Props {
        /** Invoked when the user clicks the close button in the panel header. */
        onClose: () => void;
        /** Collection whose tags the editor validates tag names against. */
        collectionId: string;
    }

    type OnSaveHandler = ComponentProps<typeof QueryEditor>['onSave'];

    const { onClose, collectionId }: Props = $props();
    const { tags, isLoading, error } = $derived(useTags({ collection_id: collectionId }));
    // Skip the tag check until the tags are known, to avoid false warnings.
    const tagNames = $derived($isLoading || $error ? undefined : $tags.map((tag) => tag.name));
    const { imageQueryExpression, updateQueryExpr } = useImageFilters();
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
        <Typography
            variant="body2"
            component="div"
            className="mt-1 min-w-0 break-words text-muted-foreground [&_code]:break-all"
        >
            <p>Write a query expression to filter your dataset. Available syntax:</p>
            <ul class="my-1 ml-4 list-disc space-y-1">
                <li>Logical operations: <code>AND</code>, <code>OR</code>, <code>NOT</code></li>
                <li>
                    Image fields: <code>file_name</code>, <code>file_path_abs</code>,
                    <code>width</code>, <code>height</code>, <code>created_at</code>
                </li>
                <li>Metadata: <code>metadata["quality_score"] &gt;= 0.8</code></li>
                <li>
                    Sample evaluation: <code
                        >sample_evaluation(name = "run-name" AND "tp" &gt;= 1)</code
                    >
                </li>
                <li>Tag membership: <code>"tag_name" IN tags</code></li>
                <li>
                    Annotation conditions: <code>segmentation_mask(…)</code>,
                    <code>object_detection(…)</code>, <code>classification(…)</code>
                </li>
            </ul>
            <p>Tip: Completion hints will appear as you type a space or a left parenthesis.</p>
        </Typography>
    </div>
    <QueryEditor
        height="100%"
        value={$imageQueryExpression?.query_expr_str}
        {tagNames}
        onSave={handleQueryEditorValueChange}
    />
</div>
