<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import QueryEditor from '$lib/components/QueryEditor/QueryEditor.svelte';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';

    type OnSaveHandler = ComponentProps<typeof QueryEditor>['onSave'];

    const { updateQueryExpr } = useImageFilters();

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
    };
</script>

<div class="flex h-full flex-1 flex-col rounded-[1vw] bg-card p-4">
    <div class="mb-3">
        <h2 class="text-lg font-semibold text-foreground">Query Filter</h2>
        <div class="mt-1 text-sm text-muted-foreground">
            <p>Write a query expression to filter your dataset. Available syntax:</p>
            <ul class="my-1.5 ml-4 list-disc space-y-1.5">
                <li>Logical operations: <code>AND</code>, <code>OR</code>, <code>NOT</code></li>
                <li>
                    Image fields: <code>file_name</code>, <code>file_name_abs</code>,
                    <code>width</code>, <code>height</code>, <code>created_at</code>
                </li>
                <li>Tag membership: <code>"tag_name" IN tags</code></li>
                <li>
                    Annotation conditions: <code>segmentation_mask(…)</code>,
                    <code>object_detection(…)</code>, <code>classification(…)</code>
                </li>
            </ul>
            <p>Tip: Completion hints will show as you type a space or a left parenthesis.</p>
        </div>
    </div>
    <QueryEditor height="100%" onSave={handleQueryEditorValueChange} />
</div>
