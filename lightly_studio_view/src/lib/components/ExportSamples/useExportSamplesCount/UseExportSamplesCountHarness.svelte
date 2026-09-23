<script lang="ts">
    import type { ImageFilter } from '$lib/api/lightly_studio_local';
    import { useExportSamplesCount } from './useExportSamplesCount.svelte';

    interface Props {
        collectionId: string;
        collectionFilter?: ImageFilter | null;
        onReady: (result: ReturnType<typeof useExportSamplesCount>) => void;
    }

    let { collectionId, collectionFilter, onReady }: Props = $props();

    const result = useExportSamplesCount(() => ({
        collection_id: collectionId,
        collectionFilter
    }));

    $effect(() => {
        onReady(result);
    });
</script>
