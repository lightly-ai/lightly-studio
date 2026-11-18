<script lang="ts">
    import { WORKFLOW_STATES, isWorkflowFileState } from '../workflowFileTexts';

    interface Props {
        /** The sample's batch file state. Any other value shows no badge. */
        state: string;
        /** Show only the coloured dot, for tiles too narrow for the label. */
        compact?: boolean;
    }

    const { state, compact = false }: Props = $props();

    const style = $derived(isWorkflowFileState(state) ? WORKFLOW_STATES[state] : null);
</script>

{#if style}
    <!-- The width cap leaves the top-right corner free for the selection box. -->
    <div
        data-testid="workflow-grid-state-badge"
        data-state={state}
        title={style.label}
        aria-label={compact ? style.label : undefined}
        role={compact ? 'img' : undefined}
        class="pointer-events-none absolute left-1 top-1 z-10 flex h-5 max-w-[calc(100%-2.5rem)] items-center gap-1.5 whitespace-nowrap rounded bg-black/60 px-1.5 text-xs font-medium text-white backdrop-blur-sm"
    >
        <span
            data-testid="workflow-grid-state-dot"
            class="size-2 shrink-0 rounded-full"
            style:background-color={style.color}
            aria-hidden="true"
        ></span>
        {#if !compact}
            <span data-testid="workflow-grid-state-label" class="min-w-0 truncate"
                >{style.label}</span
            >
        {/if}
    </div>
{/if}
