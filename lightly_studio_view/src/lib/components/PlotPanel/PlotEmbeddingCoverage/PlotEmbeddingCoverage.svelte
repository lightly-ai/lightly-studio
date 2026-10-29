<script lang="ts">
    import type { AnnotationsFilter } from '$lib/api/lightly_studio_local';
    import { Select } from '$lib/components/Select';
    import { useAnnotationEmbeddingCoverage } from '$lib/hooks/useAnnotationEmbeddingCoverage/useAnnotationEmbeddingCoverage.svelte';
    import { useAnnotationHasEmbeddingFilter } from '$lib/hooks/useAnnotationHasEmbeddingFilter/useAnnotationHasEmbeddingFilter';
    import {
        HAS_EMBEDDING_ITEMS,
        fromHasEmbeddingValue,
        getCoverageText,
        toHasEmbeddingValue
    } from './embeddingCoverage';

    interface Props {
        collectionId: string;
        filter: AnnotationsFilter | undefined;
    }

    let { collectionId, filter }: Props = $props();

    const coverageQuery = useAnnotationEmbeddingCoverage(() => ({ collectionId, filter }));
    const { hasEmbedding, setHasEmbedding } = useAnnotationHasEmbeddingFilter();

    const coverageText = $derived(getCoverageText(coverageQuery.data));
</script>

{#if coverageText !== null || $hasEmbedding !== undefined}
    <div class="flex items-center gap-2 text-sm text-muted-foreground">
        {#if coverageText !== null}
            <span data-testid="plot-embedding-coverage">{coverageText}</span>
        {/if}
        <Select
            items={HAS_EMBEDDING_ITEMS}
            value={toHasEmbeddingValue($hasEmbedding)}
            size="xs"
            testId="plot-has-embedding-select"
            onValueChange={(value) => setHasEmbedding(fromHasEmbeddingValue(value))}
        />
    </div>
{/if}
