<script lang="ts">
    // Stands in for SelectList so a test can pick a class with one click.
    const { onSelect }: { onSelect?: (item: { value: string; label: string }) => void } = $props();
</script>

<button data-testid="pick-class" onclick={() => onSelect?.({ value: 'crack', label: 'crack' })}>
    pick
</button>
