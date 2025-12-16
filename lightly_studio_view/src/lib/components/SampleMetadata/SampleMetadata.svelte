<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { formatInteger } from '$lib/utils';
    import MetadataSegment from '../MetadataSegment/MetadataSegment.svelte';

    type Image = {
        file_name: string;
        file_path_abs: string;
        width: number;
        height: number;
        metadata_dict?: unknown | null;
    };

    const {
        sample,
        showCustomMetadata = true
    }: {
        sample: Image;
        showCustomMetadata?: boolean;
    } = $props();

    const sample_details = $derived([
        { id: 'height', label: 'Height:', value: formatInteger(sample.height) + 'px' },
        { id: 'width', label: 'Width:', value: formatInteger(sample.width) + 'px' },
        { id: 'filename', label: 'Filename:', value: sample.file_name },
        { id: 'filepath', label: 'Filepath:', value: sample.file_path_abs }
    ]);
</script>

<Segment title="Sample details">
    <div class="grid grid-cols-[6rem_1fr] gap-y-3 text-diffuse-foreground">
        {#each sample_details as { label, value, id } (label)}
            <span class="text-sm">{label}</span>
            <span class="break-all text-sm" data-testid={`sample-metadata-${id}`}>{value}</span>
        {/each}
    </div>
</Segment>

{#if showCustomMetadata}
    <MetadataSegment metadata_dict={sample.metadata_dict} />
{/if}
