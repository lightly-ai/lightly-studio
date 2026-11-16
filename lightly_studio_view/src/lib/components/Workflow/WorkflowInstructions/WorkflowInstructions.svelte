<script lang="ts">
    import { Segment } from '$lib/components';
    import type { WorkflowFile } from '$lib/hooks';
    import { FileText } from '@lucide/svelte';

    interface Props {
        file: Pick<
            WorkflowFile,
            'instructions' | 'instructions_updated_by' | 'instructions_updated_at'
        >;
    }

    const { file }: Props = $props();

    const edited = $derived(
        file.instructions_updated_at
            ? new Date(file.instructions_updated_at).toLocaleString()
            : null
    );
</script>

<Segment title="Instructions" icon={FileText}>
    {#if file.instructions}
        <p class="whitespace-pre-wrap text-sm">{file.instructions}</p>
    {:else}
        <p class="text-sm text-muted-foreground">No instructions for this batch.</p>
    {/if}
    {#if file.instructions_updated_by && edited}
        <p class="mt-2 text-xs text-muted-foreground">
            Last edited by {file.instructions_updated_by} · {edited}
        </p>
    {/if}
</Segment>
