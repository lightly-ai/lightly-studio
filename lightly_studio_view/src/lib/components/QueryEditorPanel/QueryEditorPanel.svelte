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
    <QueryEditor height="100%" onSave={handleQueryEditorValueChange} />
</div>
