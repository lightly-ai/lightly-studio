<script lang="ts">
    import type { useAutoLabelRun } from './useAutoLabelRun.svelte';
    interface Props {
        summary: NonNullable<ReturnType<typeof useAutoLabelRun>['run']['data']>;
    }
    let { summary }: Props = $props();
</script>

{#if summary.unmatched_prompts.length}
    <div class="rounded border border-amber-500 p-3" role="status">
        <p class="font-medium">Prompts with no matches</p>
        <p class="break-words text-sm">{summary.unmatched_prompts.join(', ')}</p>
    </div>
{:else}
    <p class="text-sm">Every prompt matched at least one annotation.</p>
{/if}
<dl class="grid grid-cols-2 gap-2 text-sm">
    <dt>Annotations created</dt>
    <dd>{summary.annotations_created}</dd>
    <dt>Images processed</dt>
    <dd>{summary.images_processed}</dd>
    <dt>Images skipped</dt>
    <dd>{summary.images_skipped}</dd>
    <dt>Annotation source</dt>
    <dd class="break-words">{summary.source_name}</dd>
</dl>
