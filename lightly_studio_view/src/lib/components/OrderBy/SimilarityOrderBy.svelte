<script lang="ts">
    import { useSimilaritySort } from '$lib/hooks/useSimilaritySort';
    import OrderByControl from './OrderByControl.svelte';

    const { direction, toggleDirection } = useSimilaritySort();
</script>

<OrderByControl
    items={[]}
    selectedValue=""
    triggerLabel="Similarity"
    direction={$direction}
    fieldLocked
    onValueChange={() => {}}
    onOpen={() => {}}
    onToggleDirection={toggleDirection}
/>
