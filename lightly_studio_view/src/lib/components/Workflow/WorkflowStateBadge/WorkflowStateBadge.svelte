<script lang="ts">
    import { WORKFLOW_STATES, isWorkflowFileState } from '../workflowFileTexts';

    interface Props {
        /** The sample's batch file state. Any other value shows no badge. */
        state: string;
    }

    const { state }: Props = $props();

    const style = $derived(isWorkflowFileState(state) ? WORKFLOW_STATES[state] : null);
</script>

{#if style}
    <div
        data-testid="workflow-grid-state-badge"
        data-state={state}
        class="pointer-events-none absolute left-1 top-1 z-10 flex h-5 items-center gap-1.5 rounded bg-black/60 px-1.5 text-xs font-medium text-white backdrop-blur-sm"
    >
        <span
            data-testid="workflow-grid-state-dot"
            class="size-2 rounded-full"
            style:background-color={style.color}
            aria-hidden="true"
        ></span>{style.label}
    </div>
{/if}
