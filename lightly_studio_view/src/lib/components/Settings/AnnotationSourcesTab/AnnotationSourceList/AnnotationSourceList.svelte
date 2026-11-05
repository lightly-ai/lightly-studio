<script lang="ts">
    import { AnnotationSourceRow } from '../AnnotationSourceRow';

    interface AnnotationSourceItem {
        collection_id: string;
        name: string;
        annotation_count: number;
    }

    interface Props {
        sources: AnnotationSourceItem[];
        isLoading: boolean;
        isError: boolean;
        onDelete: (source: AnnotationSourceItem) => void;
    }

    const { sources, isLoading, isError, onDelete }: Props = $props();
</script>

<ul class="mx-auto flex max-w-lg flex-col">
    {#if isLoading}
        <li class="px-2 py-3 text-sm text-muted-foreground">Loading annotation sources…</li>
    {:else if isError}
        <li class="px-2 py-3 text-sm text-muted-foreground">
            Could not load the annotation sources.
        </li>
    {/if}
    {#each sources as source (source.collection_id)}
        <AnnotationSourceRow
            name={source.name}
            annotationCount={source.annotation_count}
            onDelete={() => onDelete(source)}
        />
    {/each}
</ul>
