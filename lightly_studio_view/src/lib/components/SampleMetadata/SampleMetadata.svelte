<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { formatInteger, formatMetadataValue } from '$lib/utils';
    import type { SampleView } from '$lib/api/lightly_studio_local';

    type MetadataDict = {
        data: Record<string, unknown>;
    };

    const {
        sample,
        showCustomMetadata = true
    }: {
        sample: SampleView;
        showCustomMetadata?: boolean;
    } = $props();

    const sample_details = $derived([
        { id: 'height', label: 'Height:', value: formatInteger(sample.height) + 'px' },
        { id: 'width', label: 'Width:', value: formatInteger(sample.width) + 'px' },
        { id: 'filename', label: 'Filename:', value: sample.file_name },
        { id: 'filepath', label: 'Filepath:', value: sample.file_path_abs }
    ]);

    // Use derived value for proper reactivity when sample changes
    const metadata = $derived.by(() => {
        // Add metadata from sample.metadata_dict.data if it exists
        const customMetadata: Array<{
            id: string;
            label: string;
            value: string;
            isComplex: boolean;
        }> = [];

        if (
            sample.metadata_dict &&
            typeof sample.metadata_dict === 'object' &&
            'data' in sample.metadata_dict
        ) {
            const metadataData = (sample.metadata_dict as MetadataDict).data;
            if (metadataData && typeof metadataData === 'object') {
                Object.entries(metadataData).forEach(([key, value]) => {
                    const formattedValue = formatMetadataValue(value);
                    const isComplex =
                        typeof value === 'object' && value !== null && !Array.isArray(value);
                    customMetadata.push({
                        id: `metadata_${key}`,
                        label: `${key}:`,
                        value: formattedValue,
                        isComplex
                    });
                });
            }
        }
        return customMetadata;
    });
</script>

<Segment title="Sample details">
    <div class="grid grid-cols-[6rem_1fr] gap-y-3 text-diffuse-foreground">
        {#each sample_details as { label, value, id } (label)}
            <span class="text-sm">{label}</span>
            <span class="break-all text-sm" data-testid={`sample-metadata-${id}`}>{value}</span>
        {/each}
    </div>
</Segment>

{#if showCustomMetadata && metadata.length > 0}
    <Segment title="Metadata">
        <div class="space-y-3 text-diffuse-foreground">
            {#each metadata as { label, value, id, isComplex } (label)}
                {#if isComplex}
                    <!-- Complex objects on same line with offset -->
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title={label}>{label}</span>
                        <pre
                            class="min-w-[8rem] flex-1 overflow-x-auto whitespace-pre-wrap rounded bg-muted p-2 text-sm">{value}</pre>
                    </div>
                {:else}
                    <!-- Simple values use the grid layout -->
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title={label}>{label}</span>
                        <span
                            class="min-w-[8rem] flex-1 break-all text-sm"
                            data-testid={`sample-metadata-${id}`}>{value}</span
                        >
                    </div>
                {/if}
            {/each}
        </div>
    </Segment>
{/if}
