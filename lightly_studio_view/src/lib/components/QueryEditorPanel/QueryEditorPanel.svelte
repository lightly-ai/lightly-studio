<script lang="ts">
    import QueryEditor from '$lib/components/QueryEditor/QueryEditor.svelte';
    import type { QueryExpr } from '$lib/api/lightly_studio_local';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';

    const { updateQueryExpr } = useImageFilters();

    const dummyQueryExpr: QueryExpr = {
        match_expr: {
            type: 'integer_expr',
            field: { table: 'image', name: 'width' },
            operator: '>',
            value: 500
        }
    };

    const handleQueryEditorValueChange = (value: string) => {
        updateQueryExpr({
            query_expr: dummyQueryExpr,
            query_expr_str: value
        });
    };
</script>

<div class="flex h-full flex-1 flex-col rounded-[1vw] bg-card p-4">
    <QueryEditor height="100%" onSave={handleQueryEditorValueChange} />
</div>
