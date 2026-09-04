<script lang="ts">
    interface Props {
        selectedCount: number;
        disabled: boolean;
        isLoading: boolean;
        collectionId: string;
        onSelect: (item: { value: string; label: string }) => void;
        onDelete: () => Promise<void> | void;
    }

    let { selectedCount, onSelect, onDelete }: Props = $props();
</script>

<button
    data-testid="mock-select-label"
    onclick={() => onSelect({ value: 'new-label', label: 'New Label' })}
>
    Select Label
</button>
<button data-testid="mock-delete-annotations" onclick={onDelete}>
    Delete {selectedCount}
</button>
