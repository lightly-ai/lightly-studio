<script lang="ts">
    interface Props {
        selectedCount: number;
        disabled: boolean;
        isLoading: boolean;
        collectionId: string;
        onSelect: (item: { value: string; label: string }) => void;
    }

    let { onSelect }: Props = $props();
</script>

<button
    data-testid="mock-select-label"
    onclick={() => onSelect({ value: 'new-label', label: 'New Label' })}
>
    Select Label
</button>
