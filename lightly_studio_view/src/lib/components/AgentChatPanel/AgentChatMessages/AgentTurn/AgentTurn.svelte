<script lang="ts">
    import Sparkles from '@lucide/svelte/icons/sparkles';
    import AgentChatSuggestions from '../../AgentChatSuggestions/AgentChatSuggestions.svelte';
    import type { Suggestion } from '../../AgentChatSuggestions/suggestions';
    import { STOPPED, type ChatTurn } from '../../useAgentChat/chatHistory';
    import AgentReply from '../AgentReply/AgentReply.svelte';
    import AgentActivity from './AgentActivity/AgentActivity.svelte';
    import AgentProgress from './AgentProgress/AgentProgress.svelte';
    import AgentTurnError from './AgentTurnError/AgentTurnError.svelte';
    import AgentCollectionOverview from './AgentCollectionOverview/AgentCollectionOverview.svelte';
    import { describeTurn } from './AgentTurn.helpers';

    interface Props {
        turn: ChatTurn;
        liveText: string;
        /** The reasoning of the step that the agent writes now. */
        liveReasoning: string;
        suggestions: Suggestion[];
        suggestionsDisabled: boolean;
        onPick: (prompt: string) => void;
        onEdit: (prompt: string) => void;
    }

    const {
        turn,
        liveText,
        liveReasoning,
        suggestions,
        suggestionsDisabled,
        onPick,
        onEdit
    }: Props = $props();
    const view = $derived(describeTurn(turn));
    // The streamed answer text shows the progress itself.
    const showProgress = $derived(turn.status === 'running' && (view.runningToolName || !liveText));
</script>

<article class="flex min-w-0 flex-col gap-4" aria-label="Conversation turn">
    <p
        class="max-w-[90%] self-end whitespace-pre-wrap break-words rounded-2xl rounded-br-sm bg-primary/10 px-3.5 py-2.5 text-sm leading-relaxed"
        data-testid="agent-chat-user"
    >
        <span class="sr-only">You</span>{turn.prompt}
    </p>

    <div class="flex min-w-0 flex-col gap-2.5">
        <div class="flex items-center gap-2 text-xs font-semibold">
            <span class="grid size-6 place-items-center rounded-lg bg-primary/10 text-primary">
                <Sparkles class="size-3.5" aria-hidden="true" />
            </span>
            AI Agent
        </div>
        {#if view.overview}
            <AgentCollectionOverview overview={view.overview} />
        {/if}
        <AgentActivity entries={view.activity} status={turn.status} durationMs={view.durationMs} />
        {#if !view.overview}
            {#if showProgress}
                <AgentProgress
                    runningToolName={view.runningToolName}
                    {liveReasoning}
                    latestStep={view.latestStep}
                    startedAt={turn.startedAt ?? Date.now()}
                />
            {/if}
            {#each view.answers as answer, index (index)}
                <AgentReply text={answer} />
            {/each}
            {#if liveText}
                <AgentReply text={liveText} isStreaming />
            {/if}
        {/if}
        {#if view.replyError}
            <AgentTurnError
                message={view.replyError}
                isStopped={turn.error === STOPPED}
                canResend={view.canResend}
                disabled={suggestionsDisabled}
                onRetry={() => onPick(turn.prompt)}
                onEdit={() => onEdit(turn.prompt)}
            />
        {/if}
        {#if suggestions.length}
            <AgentChatSuggestions {suggestions} disabled={suggestionsDisabled} {onPick} />
        {/if}
    </div>
</article>
