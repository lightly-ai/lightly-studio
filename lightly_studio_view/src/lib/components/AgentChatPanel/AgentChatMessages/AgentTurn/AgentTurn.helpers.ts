import { isActivityEntry, toChatEntries } from '../../toChatEntries';
import type { ChatTurn } from '../../useAgentChat/chatHistory';
import { getCollectionOverview } from './AgentCollectionOverview/collectionOverview';

const NO_ANSWER =
    'The agent finished without a written answer. Check the activity before sending again.';

/** Splits a saved turn into the parts that the turn shows. */
export function describeTurn(turn: ChatTurn) {
    const entries = toChatEntries(turn.messages);
    const activity = entries.filter(isActivityEntry);
    const answers = entries.flatMap((entry) => (entry.kind === 'assistant' ? [entry.text] : []));
    const overview = getCollectionOverview(turn.prompt, turn.messages);
    const hasNoAnswer = !overview && !answers.length;
    return {
        activity,
        answers,
        overview,
        runningToolName: activity.flatMap((entry) =>
            entry.kind === 'tool' && entry.status === 'running' ? [entry.name] : []
        )[0],
        latestStep: activity.flatMap((entry) => (entry.kind === 'step' ? [entry.text] : [])).at(-1),
        durationMs:
            turn.startedAt && turn.finishedAt ? turn.finishedAt - turn.startedAt : undefined,
        replyError: turn.error ?? (turn.status === 'done' && hasNoAnswer ? NO_ANSWER : undefined),
        canResend: turn.status === 'failed' || hasNoAnswer
    };
}
