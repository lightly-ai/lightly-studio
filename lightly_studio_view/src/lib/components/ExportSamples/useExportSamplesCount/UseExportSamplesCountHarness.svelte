<script lang="ts">
    import type { ImageFilter } from '$lib/api/lightly_studio_local';
    import type { ExportFilter } from '$lib/services/types';
    import { useExportSamplesCount } from './useExportSamplesCount.svelte';

    interface Props {
        collection_id: string;
        includeFilter?: ExportFilter;
        excludeFilter?: ExportFilter;
        collectionFilter?: ImageFilter | null;
        onReady: (result: ReturnType<typeof useExportSamplesCount>) => void;
    }

    let { collection_id, includeFilter, excludeFilter, collectionFilter, onReady }: Props =
        $props();

    const result = useExportSamplesCount(() => ({
        collection_id,
        includeFilter,
        excludeFilter,
        collectionFilter
    }));

    onReady(result);
</script>
