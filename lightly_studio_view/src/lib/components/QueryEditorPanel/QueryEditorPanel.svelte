<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { X } from '@lucide/svelte';
    import QueryEditor from '$lib/components/QueryEditor/QueryEditor.svelte';
    import { Button } from '$lib/components/ui/button';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';

    interface Props {
        /** Invoked when the user clicks the close button in the panel header. */
        onClose: () => void;
    }

    type OnSaveHandler = ComponentProps<typeof QueryEditor>['onSave'];

    const { onClose }: Props = $props();
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

<div class="flex h-full min-w-0 flex-1 flex-col rounded-[1vw] bg-card p-4">
    <div class="mb-3 min-w-0">
        <div class="flex items-center justify-between">
            <Typography variant="h5" component="h2" className="text-foreground"
                >Query Filter</Typography
            >
            <Button
                variant="ghost"
                size="icon"
                onclick={onClose}
                aria-label="Close query filter panel"
                class="h-8 w-8"
                data-testid="query-editor-close-button"
            >
                <X class="size-4" />
            </Button>
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
                <li>Tag membership: <code>"tag_name" IN tags</code></li>
                <li>
                    Annotation conditions: <code>segmentation_mask(…)</code>,
                    <code>object_detection(…)</code>, <code>classification(…)</code>
                </li>
            </ul>
            <p>Tip: Completion hints will show as you type a space or a left parenthesis.</p>
        </Typography>
    </div>
    <QueryEditor height="100%" onSave={handleQueryEditorValueChange} />
</div>
