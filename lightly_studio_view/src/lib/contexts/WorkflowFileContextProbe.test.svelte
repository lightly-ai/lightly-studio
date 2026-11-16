<script lang="ts">
    import { onMount } from 'svelte';
    import { createWorkflowFileContext } from './WorkflowFile.svelte';

    interface Props {
        onContext: (context: ReturnType<typeof createWorkflowFileContext>) => void;
    }

    const { onContext }: Props = $props();

    const context = createWorkflowFileContext(() => ({
        projectId: 'p1',
        batchId: 'b1',
        sampleId: 's1'
    }));
    onMount(() => onContext(context));
</script>

<span data-testid="probe-state">{context.file?.state ?? 'loading'}</span>
