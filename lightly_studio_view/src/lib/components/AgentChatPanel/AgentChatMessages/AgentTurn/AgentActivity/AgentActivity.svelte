<script lang="ts">
    import ChevronDown from '@lucide/svelte/icons/chevron-down';
    import type { ActivityEntry } from '../../../toChatEntries';
    import type { ChatTurn } from '../../../useAgentChat/chatHistory';
    import { formatDuration, toPlainReasoning } from '../AgentProgress/agentProgress';
    import { formatToolActivity } from './toolActivity';

    interface Props {
        /** The thoughts, step sentences and tool calls of the turn, in order. */
        entries: ActivityEntry[];
        status: ChatTurn['status'];
        /** How long the turn took, once it ended. */
        durationMs?: number;
    }

    const { entries, status, durationMs }: Props = $props();
    const isRunning = $derived(status === 'running');
    const tools = $derived(entries.filter((entry) => entry.kind === 'tool'));
    const latestResult = $derived(
        tools.findLast((tool) => tool.status === 'done' && tool.summary !== 'done')
    );
    const failedTools = $derived(tools.filter((tool) => tool.status === 'error').length);
    const summary = $derived(
        [
            durationMs === undefined ? undefined : `Worked for ${formatDuration(durationMs)}`,
            failedTools ? `${failedTools} failed` : latestResult?.summary
        ]
            .filter(Boolean)
            .join(' · ')
    );
</script>

{#if entries.length}
    <details
        class="group rounded-lg border border-border/70 px-2.5 py-1.5 text-xs text-muted-foreground"
    >
        <summary
            class="flex cursor-pointer list-none items-center gap-1.5 py-1 [&::-webkit-details-marker]:hidden"
        >
            <ChevronDown class="size-3.5 shrink-0 group-open:rotate-180" aria-hidden="true" />
            <span>Activity{summary ? ` · ${summary}` : ''}</span>
        </summary>
        <ul class="space-y-2 py-1.5">
            {#each entries as entry, index (index)}
                <li class="break-words">
                    {#if entry.kind === 'thinking'}
                        <span class="font-medium text-foreground">Thought</span>
                        <span class="block whitespace-pre-wrap">
                            {toPlainReasoning(entry.text)}
                        </span>
                    {:else if entry.kind === 'step'}
                        <span class="block text-foreground/80">{entry.text}</span>
                    {:else if entry.kind === 'tool'}
                        {@const toolStatus =
                            !isRunning && entry.status === 'running' ? 'interrupted' : entry.status}
                        <span class="font-medium text-foreground">
                            {formatToolActivity(entry.name, toolStatus)}
                        </span>
                        {#if toolStatus === 'error' || (toolStatus === 'done' && entry.summary !== 'done')}
                            <span class="block">{entry.summary}</span>
                        {/if}
                    {/if}
                </li>
            {/each}
        </ul>
    </details>
{/if}
