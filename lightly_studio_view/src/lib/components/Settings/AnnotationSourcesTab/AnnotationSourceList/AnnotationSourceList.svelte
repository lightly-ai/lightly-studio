<script lang="ts">
    import { AnnotationClassAddRow } from '../../AnnotationClassesTab/AnnotationClassAddRow';
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
        // The name to offer for adding. Empty when no source can be added.
        addName: string;
        // The add row is the only match, so it comes first and Enter adds the source.
        isAddEnterTarget: boolean;
        highlightedId: string | null;
        defaultName: string | null;
        onAdd: () => void;
        onRename: (source: AnnotationSourceItem, name: string) => Promise<unknown>;
        onDelete: (source: AnnotationSourceItem) => void;
        onToggleDefault: (source: AnnotationSourceItem) => void;
    }

    const {
        sources,
        isLoading,
        isError,
        addName,
        isAddEnterTarget,
        highlightedId,
        defaultName,
        onAdd,
        onRename,
        onDelete,
        onToggleDefault
    }: Props = $props();
    const kind = 'annotation source';
</script>

<ul class="mx-auto flex max-w-lg flex-col">
    {#if addName && isAddEnterTarget}
        <AnnotationClassAddRow name={addName} isEnterTarget {onAdd} {kind} />
    {/if}
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
            isHighlighted={source.collection_id === highlightedId}
            isDefault={source.name === defaultName}
            onToggleDefault={() => onToggleDefault(source)}
            onRename={(name) => onRename(source, name)}
            onDelete={() => onDelete(source)}
        />
    {/each}
    {#if addName && !isAddEnterTarget}
        <AnnotationClassAddRow name={addName} isEnterTarget={false} {onAdd} {kind} />
    {/if}
</ul>
