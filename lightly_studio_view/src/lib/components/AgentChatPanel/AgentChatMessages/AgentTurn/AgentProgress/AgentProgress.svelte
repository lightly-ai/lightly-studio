<script lang="ts">
    import { useElapsedTime } from '../../../useElapsedTime/useElapsedTime';
    import { formatToolActivity } from '../AgentActivity/toolActivity';
    import { formatDuration, latestReasoningHeading, toPlainReasoning } from './agentProgress';

    interface Props {
        /** The name of the tool that runs now, if any. */
        runningToolName?: string;
        /** The reasoning of the step that the model writes now. */
        liveReasoning: string;
        /** The latest sentence in which the agent tells its next step, if any. */
        latestStep?: string;
        startedAt: number;
    }

    const { runningToolName, liveReasoning, latestStep, startedAt }: Props = $props();
    const elapsed = $derived(useElapsedTime(startedAt));
    const heading = $derived(latestReasoningHeading(liveReasoning));
    const isThinking = $derived(!runningToolName && Boolean(liveReasoning.trim()));
    const label = $derived.by(() => {
        if (runningToolName) return formatToolActivity(runningToolName, 'running');
        if (isThinking) return heading ? `Thinking · ${heading}` : 'Thinking…';
        return latestStep ?? 'Preparing a reply…';
    });
</script>

<div class="flex min-w-0 flex-col gap-1.5" data-testid="agent-progress">
    <p class="flex items-start gap-2 text-xs text-muted-foreground">
        <span
            class="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary motion-safe:animate-pulse"
            aria-hidden="true"
        ></span>
        <span class="line-clamp-2 flex-1" aria-live="polite" data-testid="agent-activity-progress">
            {label}
        </span>
        <span class="shrink-0 tabular-nums" aria-label="Elapsed time">
            {formatDuration($elapsed)}
        </span>
    </p>
    {#if isThinking}
        <!-- The newest lines stay at the bottom; older lines leave the box at the top. -->
        <div
            class="flex max-h-24 flex-col justify-end overflow-hidden rounded-lg border border-border/60 bg-muted/30 px-2.5 pb-1.5 pt-3 text-xs leading-5 text-muted-foreground [mask-image:linear-gradient(to_bottom,transparent,black_0.75rem)]"
            data-testid="agent-thinking-preview"
        >
            <p class="whitespace-pre-wrap break-words">{toPlainReasoning(liveReasoning)}</p>
        </div>
    {/if}
</div>
