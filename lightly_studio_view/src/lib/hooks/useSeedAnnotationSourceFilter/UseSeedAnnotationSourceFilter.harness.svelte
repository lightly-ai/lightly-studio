<script lang="ts">
    import { useSeedAnnotationSourceFilter } from './useSeedAnnotationSourceFilter.svelte';

    // The hook runs a $effect, which needs a component instance to attach to.
    interface Props {
        collectionId: string;
    }

    let { collectionId }: Props = $props();

    useSeedAnnotationSourceFilter(() => collectionId);
</script>
