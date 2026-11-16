<script lang="ts">
    import type { WorkflowFile } from '$lib/hooks';
    import { Lock } from '@lucide/svelte';
    import { readOnlyText } from '../workflowFileTexts';

    interface Props {
        file: Pick<WorkflowFile, 'state' | 'can_edit' | 'your_role' | 'labeler' | 'reviewer'>;
    }

    const { file }: Props = $props();

    const text = $derived(readOnlyText(file));
</script>

{#if text}
    <div
        role="status"
        class="flex items-center gap-2 rounded-md border bg-muted px-3 py-2 text-sm text-muted-foreground"
    >
        <Lock class="size-4 shrink-0" aria-hidden="true" />
        {text}
    </div>
{/if}
