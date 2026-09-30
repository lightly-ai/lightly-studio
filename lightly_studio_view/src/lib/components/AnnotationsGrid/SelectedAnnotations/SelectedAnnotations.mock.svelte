<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';

    interface Props {
        selectedAnnotations: AnnotationView[];
        disabled: boolean;
        isLoading: boolean;
        collectionId: string;
        onSelect: (item: { value: string; label: string }) => void;
        selectedCount: number;
        onDelete: () => Promise<void>;
    }

    let { onSelect, selectedCount, onDelete }: Props = $props();
</script>

<button
    data-testid="mock-select-label"
    onclick={() => onSelect({ value: 'new-label', label: 'New Label' })}
>
    Select Label
</button>

<button data-testid="mock-delete-annotations" onclick={() => onDelete()}>
    Delete {selectedCount}
</button>
