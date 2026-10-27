<script lang="ts">
    import { AnnotationClassAddRow } from '../AnnotationClassAddRow';
    import { AnnotationClassRow } from '../AnnotationClassRow';

    interface AnnotationClassItem {
        annotation_label_id?: string;
        annotation_label_name: string;
        annotation_count: number;
    }

    interface Props {
        classes: AnnotationClassItem[];
        isLoading: boolean;
        // The name to offer for adding. Empty when no class can be added.
        addName: string;
        // The add row is the only match, so it comes first and Enter adds the class.
        isAddEnterTarget: boolean;
        // True when the dataset has no classes and nothing can be added.
        showEmptyHint: boolean;
        highlightedId: string | null;
        onAdd: () => void;
        onRename: (labelId: string, oldName: string, name: string) => Promise<unknown>;
        onDelete: (labelId: string) => Promise<unknown>;
    }

    const {
        classes,
        isLoading,
        addName,
        isAddEnterTarget,
        showEmptyHint,
        highlightedId,
        onAdd,
        onRename,
        onDelete
    }: Props = $props();
</script>

<ul class="mx-auto flex max-w-lg flex-col">
    {#if addName && isAddEnterTarget}
        <AnnotationClassAddRow name={addName} isEnterTarget {onAdd} />
    {/if}
    {#if isLoading}
        <li class="px-2 py-3 text-sm text-muted-foreground">Loading annotation classes…</li>
    {:else if showEmptyHint}
        <li class="px-2 py-6 text-sm text-muted-foreground">
            This dataset has no annotation classes yet. Type a name above and press Enter to add the
            first one.
        </li>
    {/if}
    {#each classes as annotationClass (annotationClass.annotation_label_id)}
        <AnnotationClassRow
            name={annotationClass.annotation_label_name}
            isHighlighted={annotationClass.annotation_label_id === highlightedId}
            annotationCount={annotationClass.annotation_count}
            onRename={(name) =>
                onRename(
                    annotationClass.annotation_label_id!,
                    annotationClass.annotation_label_name,
                    name
                )}
            onDelete={() => onDelete(annotationClass.annotation_label_id!)}
        />
    {/each}
    {#if addName && !isAddEnterTarget}
        <AnnotationClassAddRow name={addName} isEnterTarget={false} {onAdd} />
    {/if}
</ul>
