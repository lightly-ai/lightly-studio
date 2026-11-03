<script lang="ts">
    import { useSelectionTagCounts } from './useSelectionTagCounts.svelte';
    import type { SelectionTarget } from '$lib/hooks/useSelectionTarget/useSelectionTarget';

    let { target }: { target: SelectionTarget } = $props();
    const { query } = useSelectionTagCounts(() => ({ collectionId: 'c1', target }));
</script>

<div data-testid="counts">
    {[...(query.data ?? new Map())].map(([id, count]) => `${id}=${count}`).join(',')}
</div>
