<script lang="ts">
    import QueryEditor from '$lib/components/QueryEditor/QueryEditor.svelte';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import type { QueryExprTranslationResult } from '../QueryEditor/language/query-expr-translation';

    const { updateQueryExpr } = useImageFilters();

    const handleQueryEditorValueChange = (
        value: string,
        parsed: QueryExprTranslationResult | null
    ) => {
        debugger;
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
