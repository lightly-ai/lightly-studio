<script lang="ts">
    import type { ImageFilter } from '$lib/api/lightly_studio_local';
    import type { ExportFilter } from '$lib/services/types';
    import { useExportSamplesCount } from './useExportSamplesCount.svelte';

    interface Props {
        collectionId: string;
        includeFilter?: ExportFilter;
        excludeFilter?: ExportFilter;
        collectionFilter?: ImageFilter | null;
        onReady: (result: ReturnType<typeof useExportSamplesCount>) => void;
    }

    let { collectionId, includeFilter, excludeFilter, collectionFilter, onReady }: Props = $props();

    const result = useExportSamplesCount(() => ({
        collection_id: collectionId,
        includeFilter,
        excludeFilter,
        collectionFilter
    }));

    onReady(result);
</script>
