<script lang="ts">
    import type { WorkflowFile } from '$lib/hooks';
    import { TURN_COLORS, WORKFLOW_STATES, roundText, turnText } from '../workflowFileTexts';

    interface Props {
        file: Pick<WorkflowFile, 'state' | 'round' | 'your_turn' | 'waiting_for'>;
    }

    const { file }: Props = $props();

    const state = $derived(WORKFLOW_STATES[file.state]);
    const turn = $derived(turnText(file));
</script>

<div class="flex items-center gap-3 text-sm" data-testid="workflow-file-status">
    <span
        data-testid="workflow-state-badge"
        class="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-semibold"
        ><span class="size-2 rounded-full" style:background-color={state.color} aria-hidden="true"
        ></span>{state.label}</span
    >
    <span data-testid="workflow-round" class="text-muted-foreground">{roundText(file)}</span>
    <span
        data-testid="workflow-turn"
        class="font-medium"
        style:color={turn.yourTurn ? TURN_COLORS.yours : TURN_COLORS.others}>{turn.text}</span
    >
</div>
